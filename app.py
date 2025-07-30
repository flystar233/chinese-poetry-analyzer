from flask import Flask, render_template, request, jsonify
import json
import pandas as pd
import re
import os
from typing import Tuple, List, Dict, Any, Optional

app = Flask(__name__)

def build_tone_dict(rhymebook_data: List[Dict[str, Any]]) -> Tuple[Dict[str, str], Dict[str, List[str]]]:
    """
    将韵书数据预处理为字到平仄的映射字典，同时返回韵部到所有字的映射。
    """
    tone_dict = {}
    yunbu_dict = {}
    for item in rhymebook_data:
        for yunbu_name, value in item.items():
            if yunbu_name not in yunbu_dict:
                yunbu_dict[yunbu_name] = set()
            for word in value.get('平', []):
                tone_dict[word] = '平'
                yunbu_dict[yunbu_name].add(word)
            for word in value.get('仄', []):
                tone_dict[word] = '仄'
                yunbu_dict[yunbu_name].add(word)
    # 如果你需要返回list而不是set
    yunbu_dict = {k: list(v) for k, v in yunbu_dict.items()}
    return tone_dict, yunbu_dict

def load_rhymebook_with_yunbu(rhymebook_choice: str) -> Tuple[Dict[str, str], Dict[str, List[str]]]:
    """
    加载韵书文件并返回平仄字典和字到韵部的映射。
    """
    rhymebook_map = {
        '1': 'data/词林正韵.json',
        '2': 'data/中华新韵.json'
    }
    rhymebook_path = rhymebook_map.get(rhymebook_choice, 'data/词林正韵.json')
    if not os.path.exists(rhymebook_path):
        raise FileNotFoundError(f"韵书文件未找到: {rhymebook_path}")
    with open(rhymebook_path, 'r', encoding='utf-8') as f:
        rhymebook_data = json.load(f)
    return build_tone_dict(rhymebook_data)

def load_cipai(cipai_choice: str) -> pd.DataFrame:
    """
    加载词牌谱文件并返回DataFrame。
    """
    cipai_map = {
        '1': 'data/cipai_with_statistics_qdcp.csv',
        '2': 'data/cipai_with_statistics_tscgl.csv'
    }
    cipai_path = cipai_map.get(cipai_choice, 'data/cipai_with_statistics_tscgl.csv')
    if not os.path.exists(cipai_path):
        raise FileNotFoundError(f"词牌谱文件未找到: {cipai_path}")
    return pd.read_csv(cipai_path)

def load_yunjiao(filepath: str = 'data/yunjiao.csv') -> Dict[str, List[int]]:
    """
    读取韵脚文件，返回以词牌名+作者为键，韵脚位置列表为值的字典。
    假设韵脚字段全部为带引号的JSON字符串。
    """
    yunjiao_dict = {}
    df = pd.read_csv(filepath)
    for idx, row in df.iterrows():
        key = f"{row['词牌名']}|{row['作者']}"
        yunjiao_str = str(row['韵脚']).strip()
        if yunjiao_str.startswith('"') and yunjiao_str.endswith('"'):
            yunjiao_str = yunjiao_str[1:-1]
        try:
            positions = json.loads(yunjiao_str)
            yunjiao_dict[key] = positions
        except Exception as e:
            print(f"Warning:韵脚数据解析出错: {row.to_dict()}")
            continue
    return yunjiao_dict

def preprocess_text(text: str) -> Tuple[str, int, List[int]]:
    """
    只保留汉字，统计总字数和分句字数。
    """
    text_drop = re.sub("[^\u4e00-\u9fa5]", "", text)
    length = len(text_drop)
    split_length = [len(i) for i in re.split('[，。、？！]', text) if i]
    return text_drop, length, split_length

def guess_cipai_name(
    length: int, split_length: List[int], cipai_data: pd.DataFrame
) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """
    根据总字数和分句字数猜测词牌名及其平仄规则。
    """
    for row in cipai_data.itertuples():
        try:
            if length == getattr(row, '总数') and str(split_length) == getattr(row, '分段字数'):
                return getattr(row, '词牌名'), getattr(row, '作者'),getattr(row, '韵律')
        except Exception:
            continue
    return None, None, None

def mark_tone(text: str, tone_dict: Dict[str, str]) -> List[Tuple[str, str]]:
    """
    标注文本每个字的平仄属性。
    """
    tone_text = []
    for word in text:
        pz = tone_dict.get(word, None)
        if pz:
            tone_text.append((word, pz))
        else:
            tone_text.append((word, '未知'))
    return tone_text

def get_score_tone(
    tone_text: List[Tuple[str, str]], tone_database: List[str]
) -> Tuple[float, List[Tuple[Tuple[str, str], str]]]:
    """
    计算平仄得分，并找出不合平仄的字。
    """
    score = 0
    issue_data = []
    for item1, item2 in zip(tone_text, tone_database):
        if item1[1] != item2 and item2 != '中':
            issue_data.append((item1, item2))
        elif item1[1] == item2 or item2 == '中':
            score += 1
    total = len(tone_database)
    score_percent = (score / total * 100) if total else 0
    return score_percent, issue_data

def estimate_poetry(
    text: str, rhymebook: str, cipai: str
) -> Dict[str, Any]:
    """
    综合分析诗词文本，返回分析结果的字典。
    """
    try:
        tone_dict, yunbu_dict = load_rhymebook_with_yunbu(rhymebook)
    except Exception as e:
        return {"error": f"加载韵书文件出错: {e}"}
    
    try:
        cipai_data = load_cipai(cipai)
    except Exception as e:
        return {"error": f"加载词牌谱文件出错: {e}"}
    
    try:
        yunjiao_dict = load_yunjiao()
    except Exception as e:
        return {"error": f"加载韵脚文件出错: {e}"}

    text_drop, length, split_length = preprocess_text(text)
    guess_cipai, author, tone_database = guess_cipai_name(length, split_length, cipai_data)   
    
    if not tone_database:
        return {
            "success": False,
            "message": "未能匹配到词牌名，请检查输入文本或词牌谱数据。",
            "text": text,
            "processed_text": text_drop,
            "length": length,
            "split_length": split_length
        }

    # 只保留汉字的平仄规则
    tone_database = re.sub("[^\u4e00-\u9fa5]", "", tone_database)
    tone_database = list(re.sub(r"增韵", "", tone_database))
    tone_text = mark_tone(text_drop, tone_dict)
    score, issue_data = get_score_tone(tone_text, tone_database)

    # 韵脚字处理
    yunjiao_positions = []
    yunjiao_words = []
    if guess_cipai and author:
        key = f"{guess_cipai.strip()}|{author.strip()}"
        yunjiao_positions = yunjiao_dict.get(key, [])
        yunjiao_words = [text_drop[pos-1] for pos in yunjiao_positions if 0 < pos <= len(text_drop)]

    # 查询韵脚字的韵部
    yunjiao_yunbu = {}
    for word in yunjiao_words:
        yunjiao_yunbu[word] = [yunbu for yunbu, words in yunbu_dict.items() if word in words]

    # 格式化不合平仄的字信息
    formatted_issues = []
    for (word, actual), expected in issue_data:
        formatted_issues.append({
            "word": word,
            "actual": actual,
            "expected": expected
        })

    return {
        "success": True,
        "text": text,
        "processed_text": text_drop,
        "cipai_name": guess_cipai,
        "author": author,
        "score": round(score, 2),
        "issues": formatted_issues,
        "yunjiao_words": yunjiao_words,
        "yunjiao_yunbu": yunjiao_yunbu,
        "tone_text": tone_text,
        "length": length,
        "split_length": split_length
    }

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/analyze', methods=['POST'])
def analyze():
    data = request.get_json()
    text = data.get('text', '')
    rhymebook = data.get('rhymebook', '2')
    cipai = data.get('cipai', '1')
    
    if not text.strip():
        return jsonify({"error": "请输入要分析的诗词文本"})
    
    result = estimate_poetry(text, rhymebook, cipai)
    return jsonify(result)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000) 