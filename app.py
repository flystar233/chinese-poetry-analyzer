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

def load_cipai() -> pd.DataFrame:
    """
    加载钦定词谱文件并返回DataFrame。
    """
    cipai_path = 'data/cipai_with_statistics_qdcp.csv'
    if not os.path.exists(cipai_path):
        raise FileNotFoundError(f"词牌谱文件未找到: {cipai_path}")
    df = pd.read_csv(cipai_path)
    # 清理词牌名和作者名的空格
    df['词牌名'] = df['词牌名'].astype(str).str.strip()
    df['作者'] = df['作者'].astype(str).str.strip()
    return df

def load_cipai_intro() -> Dict[str, str]:
    """
    加载词牌介绍文件并返回词牌名到介绍的映射字典。
    """
    intro_path = 'data/cipai_detail_with_intro.csv'
    intro_dict = {}
    
    if not os.path.exists(intro_path):
        print(f"词牌介绍文件未找到: {intro_path}")
        return intro_dict
    
    try:
        df = pd.read_csv(intro_path)
        # 清理词牌名的空格
        df['词牌名'] = df['词牌名'].astype(str).str.strip()
        for _, row in df.iterrows():
            cipai_name = str(row['词牌名']).strip()
            intro = str(row['介绍']).strip()
            intro_dict[cipai_name] = intro
    except Exception as e:
        print(f"读取词牌介绍文件出错: {e}")
    
    return intro_dict

def load_yunjiao(filepath: str = 'data/yunjiao.csv') -> Dict[str, List[List[int]]]:
    """
    读取韵脚文件，返回以词牌名+作者为键，韵脚位置列表的列表为值的字典。
    当存在多个韵脚模式时，保存所有模式供用户选择。
    假设韵脚字段全部为带引号的JSON字符串。
    """
    yunjiao_dict = {}
    df = pd.read_csv(filepath)
    for idx, row in df.iterrows():
        # 清理词牌名和作者名的空格
        cipai_name = str(row['词牌名']).strip()
        author = str(row['作者']).strip()
        key = f"{cipai_name}|{author}"
        yunjiao_str = str(row['韵脚']).strip()
        if yunjiao_str.startswith('"') and yunjiao_str.endswith('"'):
            yunjiao_str = yunjiao_str[1:-1]
        try:
            positions = json.loads(yunjiao_str)
            # 如果键已存在，添加到列表；否则创建新列表
            if key in yunjiao_dict:
                # 检查是否已存在相同的韵脚模式，避免重复
                if positions not in yunjiao_dict[key]:
                    yunjiao_dict[key].append(positions)
            else:
                yunjiao_dict[key] = [positions]
        except Exception as e:
            print(f"Warning:韵脚数据解析出错: {row.to_dict()}")
            continue
    return yunjiao_dict

def preprocess_text(text: str) -> Tuple[str, str, int, List[int]]:
    """
    只保留汉字，统计总字数和分句字数。
    返回：处理后的纯汉字文本、清理后的原文（去除换行符）、总字数、分句字数列表
    """
    # 先去掉换行符和其他空白字符，保留标点符号用于分句
    text_cleaned = re.sub(r'\s+', '', text)  # 去掉所有空白字符（包括换行符、空格、制表符等）
    
    # 只保留汉字用于总字数统计
    text_drop = re.sub("[^\u4e00-\u9fa5]", "", text_cleaned)
    length = len(text_drop)
    
    # 按标点符号分句，并只计算每句中的汉字数量
    sentences = re.split('[，。、？！]', text_cleaned)
    split_length = [len(re.sub("[^\u4e00-\u9fa5]", "", sentence)) for sentence in sentences if sentence.strip()]
    
    return text_drop, text_cleaned, length, split_length

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
    text: str, rhymebook: str
) -> Dict[str, Any]:
    """
    综合分析诗词文本，返回分析结果的字典。
    """
    try:
        tone_dict, yunbu_dict = load_rhymebook_with_yunbu(rhymebook)
    except Exception as e:
        return {"error": f"加载韵书文件出错: {e}"}
    
    try:
        cipai_data = load_cipai()
    except Exception as e:
        return {"error": f"加载词牌谱文件出错: {e}"}
    
    try:
        yunjiao_dict = load_yunjiao()
    except Exception as e:
        return {"error": f"加载韵脚文件出错: {e}"}
    
    try:
        cipai_intro_dict = load_cipai_intro()
    except Exception as e:
        cipai_intro_dict = {}
        print(f"加载词牌介绍文件出错: {e}")

    text_drop, text_cleaned, length, split_length = preprocess_text(text)
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
    yunjiao_options = []  # 存储多个韵脚模式选项
    yunjiao_positions = []  # 默认使用第一个韵脚模式（向后兼容）
    yunjiao_words = []
    yunjiao_yunbu = {}
    yunjiao_detailed = []  # 详细的韵脚信息，包含位置、字、韵部
    
    if guess_cipai and author:
        key = f"{guess_cipai.strip()}|{author.strip()}"
        yunjiao_patterns = yunjiao_dict.get(key, [])
        
        if yunjiao_patterns:
            # 创建从text_drop位置到清理后原文位置的映射
            text_drop_to_original_map = {}
            text_drop_index = 0
            for original_index, char in enumerate(text_cleaned):
                if re.match(r'[\u4e00-\u9fa5]', char):  # 如果是汉字
                    text_drop_to_original_map[text_drop_index] = original_index
                    text_drop_index += 1
            
            # 处理每个韵脚模式
            for i, positions in enumerate(yunjiao_patterns):
                pattern_words = [text_drop[pos-1] for pos in positions if 0 < pos <= len(text_drop)]
                pattern_detailed = []
                pattern_yunbu = {}
                
                # 查询韵脚字的韵部并构建详细信息
                for pos in positions:
                    if 0 < pos <= len(text_drop):
                        word = text_drop[pos-1]
                        text_drop_pos = pos - 1  # text_drop中的位置（0开始）
                        original_pos = text_drop_to_original_map.get(text_drop_pos, -1)  # 原文中的位置
                        
                        if original_pos >= 0:
                            yunbu_list = [yunbu for yunbu, words in yunbu_dict.items() if word in words]
                            pattern_detailed.append({
                                "position": original_pos,  # 原文中的位置
                                "word": word,
                                "yunbu": yunbu_list
                            })
                            pattern_yunbu[word] = yunbu_list
                
                yunjiao_options.append({
                    "id": i,
                    "positions": positions,
                    "words": pattern_words,
                    "yunbu": pattern_yunbu,
                    "detailed": pattern_detailed
                })
            
            # 默认使用第一个模式（向后兼容）
            if yunjiao_options:
                first_option = yunjiao_options[0]
                yunjiao_positions = first_option["positions"]
                yunjiao_words = first_option["words"]
                yunjiao_yunbu = first_option["yunbu"]
                yunjiao_detailed = first_option["detailed"]

    # 格式化不合平仄的字信息
    formatted_issues = []
    for (word, actual), expected in issue_data:
        formatted_issues.append({
            "word": word,
            "actual": actual,
            "expected": expected
        })

    # 查找词牌介绍
    cipai_intro = ""
    if guess_cipai and cipai_intro_dict:
        cipai_intro = cipai_intro_dict.get(guess_cipai.strip(), "")

    return {
        "success": True,
        "text": text_cleaned,  # 使用清理后的文本，确保位置映射正确
        "original_text": text,  # 保留原始文本供参考
        "processed_text": text_drop,
        "cipai_name": guess_cipai,
        "cipai_intro": cipai_intro,  # 新增：词牌介绍
        "author": author,
        "score": round(score, 2),
        "issues": formatted_issues,
        "yunjiao_words": yunjiao_words,
        "yunjiao_yunbu": yunjiao_yunbu,
        "yunjiao_detailed": yunjiao_detailed,  # 新增：详细的韵脚信息
        "yunjiao_options": yunjiao_options,  # 新增：所有韵脚模式选项
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
    
    if not text.strip():
        return jsonify({"error": "请输入要分析的诗词文本"})
    
    result = estimate_poetry(text, rhymebook)
    return jsonify(result)

@app.route('/select_yunjiao', methods=['POST'])
def select_yunjiao():
    """
    用户选择特定韵脚模式后，重新分析并返回更新后的韵脚信息
    """
    data = request.get_json()
    text = data.get('text', '')
    rhymebook = data.get('rhymebook', '2')
    cipai_name = data.get('cipai_name', '')
    author = data.get('author', '')
    yunjiao_id = data.get('yunjiao_id', 0)
    
    if not all([text.strip(), cipai_name.strip(), author.strip()]):
        return jsonify({"error": "缺少必要参数"})
    
    try:
        tone_dict, yunbu_dict = load_rhymebook_with_yunbu(rhymebook)
        yunjiao_dict = load_yunjiao()
        
        text_drop, text_cleaned, length, split_length = preprocess_text(text)
        
        # 获取指定的韵脚模式
        key = f"{cipai_name.strip()}|{author.strip()}"
        yunjiao_patterns = yunjiao_dict.get(key, [])
        
        if not yunjiao_patterns or yunjiao_id >= len(yunjiao_patterns):
            return jsonify({"error": "未找到指定的韵脚模式"})
        
        selected_positions = yunjiao_patterns[yunjiao_id]
        
        # 创建从text_drop位置到清理后原文位置的映射
        text_drop_to_original_map = {}
        text_drop_index = 0
        for original_index, char in enumerate(text_cleaned):
            if re.match(r'[\u4e00-\u9fa5]', char):
                text_drop_to_original_map[text_drop_index] = original_index
                text_drop_index += 1
        
        # 重新计算选定韵脚模式的详细信息
        yunjiao_words = [text_drop[pos-1] for pos in selected_positions if 0 < pos <= len(text_drop)]
        yunjiao_yunbu = {}
        yunjiao_detailed = []
        
        for pos in selected_positions:
            if 0 < pos <= len(text_drop):
                word = text_drop[pos-1]
                text_drop_pos = pos - 1
                original_pos = text_drop_to_original_map.get(text_drop_pos, -1)
                
                if original_pos >= 0:
                    yunbu_list = [yunbu for yunbu, words in yunbu_dict.items() if word in words]
                    yunjiao_detailed.append({
                        "position": original_pos,
                        "word": word,
                        "yunbu": yunbu_list
                    })
                    yunjiao_yunbu[word] = yunbu_list
        
        return jsonify({
            "success": True,
            "yunjiao_words": yunjiao_words,
            "yunjiao_yunbu": yunjiao_yunbu,
            "yunjiao_detailed": yunjiao_detailed,
            "selected_yunjiao_id": yunjiao_id
        })
        
    except Exception as e:
        return jsonify({"error": f"处理韵脚选择时出错: {str(e)}"})

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)