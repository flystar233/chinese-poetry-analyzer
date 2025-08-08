from flask import Blueprint, render_template, request, jsonify, current_app
import re
import ast

from .services.analysis import (
    estimate_poetry,
    load_rhymebook_with_yunbu,
    load_yunjiao,
    preprocess_text,
    load_cipai,
    create_fillword_framework,
    get_cipai_summary_list,
)


bp = Blueprint('main', __name__)


def ok(data):
    return jsonify({"success": True, "data": data, "error": None})


def fail(error_message: str):
    return jsonify({"success": False, "data": None, "error": error_message})


@bp.route('/')
def index():
    return render_template('index.html')


@bp.route('/analyze', methods=['POST'])
def analyze():
    data = request.get_json()
    text = data.get('text', '')
    rhymebook = data.get('rhymebook', '2')

    if not text.strip():
        return fail("请输入要分析的诗词文本")

    result = estimate_poetry(text, rhymebook)
    # 统一包装
    if isinstance(result, dict) and result.get("error"):
        return fail(result.get("error"))
    if isinstance(result, dict) and result.get("success") is False:
        return fail(result.get("message") or "分析失败")

    # 去掉内部的 success/message 字段
    if isinstance(result, dict):
        data = dict(result)
        data.pop("success", None)
        data.pop("message", None)
        return ok(data)
    return ok(result)


@bp.route('/select_yunjiao', methods=['POST'])
def select_yunjiao():
    data = request.get_json()
    text = data.get('text', '')
    rhymebook = data.get('rhymebook', '2')
    cipai_name = data.get('cipai_name', '')
    author = data.get('author', '')
    yunjiao_id = data.get('yunjiao_id', 0)

    if not all([text.strip(), cipai_name.strip(), author.strip()]):
        return fail("缺少必要参数")

    try:
        tone_dict, yunbu_dict = load_rhymebook_with_yunbu(rhymebook)
        yunjiao_dict = load_yunjiao()

        text_drop, text_cleaned, length, split_length = preprocess_text(text)

        key = f"{cipai_name.strip()}|{author.strip()}"
        yunjiao_patterns = yunjiao_dict.get(key, [])
        if not yunjiao_patterns or yunjiao_id >= len(yunjiao_patterns):
            return fail("未找到指定的韵脚模式")

        selected_positions = yunjiao_patterns[yunjiao_id]

        text_drop_to_original_map = {}
        text_drop_index = 0
        for original_index, char in enumerate(text_cleaned):
            if re.match(r'[\u4e00-\u9fa5]', char):
                text_drop_to_original_map[text_drop_index] = original_index
                text_drop_index += 1

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

        return ok({
            "yunjiao_words": yunjiao_words,
            "yunjiao_yunbu": yunjiao_yunbu,
            "yunjiao_detailed": yunjiao_detailed,
            "selected_yunjiao_id": yunjiao_id
        })

    except Exception as e:
        return fail(f"处理韵脚选择时出错: {str(e)}")


@bp.route('/get_cipai_list', methods=['GET'])
def get_cipai_list():
    try:
        cipai_list, default_index = get_cipai_summary_list()
        return ok({"cipai_list": cipai_list, "default_index": default_index})
    except Exception as e:
        return fail(f"获取词牌列表失败: {str(e)}")


@bp.route('/get_fillword_framework', methods=['POST'])
def get_fillword_framework():
    data = request.get_json()
    cipai_name = data.get('cipai_name', '')
    author = data.get('author', '')
    if not all([cipai_name.strip(), author.strip()]):
        return fail("缺少词牌名或作者信息")
    try:
        cipai_data = load_cipai()
        matched_row = None
        for _, row in cipai_data.iterrows():
            if (str(row['词牌名']).strip() == cipai_name.strip() and str(row['作者']).strip() == author.strip()):
                matched_row = row
                break
        if matched_row is None:
            return fail("未找到匹配的词牌")

        tone_pattern = str(matched_row['韵律'])
        tone_pattern_cleaned = re.sub("[^\u4e00-\u9fa5]", "", tone_pattern)
        tone_pattern_list = list(re.sub(r"增韵", "", tone_pattern_cleaned))

        split_length_str = str(matched_row['分段字数'])
        try:
            split_length = ast.literal_eval(split_length_str)
        except Exception:
            split_length = []

        framework = create_fillword_framework(tone_pattern_list, split_length)
        return ok({
            "cipai_name": cipai_name,
            "author": author,
            "total_chars": int(matched_row['总数']),
            "tone_pattern": tone_pattern_list,
            "split_length": split_length,
            "framework": framework
        })
    except Exception as e:
        return fail(f"获取填词框架失败: {str(e)}")


@bp.route('/get_char_tone', methods=['POST'])
def get_char_tone():
    data = request.get_json()
    char = data.get('char', '')
    if not char:
        return fail("缺少字符参数")
    try:
        tone_dict, _ = load_rhymebook_with_yunbu('2')
        tone = tone_dict.get(char, '未知')
        if tone in ['平', '仄']:
            result_tone = tone
        elif tone == '未知':
            result_tone = '未知'
        else:
            if '平' in tone or tone in ['一声', '二声']:
                result_tone = '平'
            elif '仄' in tone or tone in ['三声', '四声', '上声', '去声', '入声']:
                result_tone = '仄'
            else:
                result_tone = '未知'
        return ok({"char": char, "tone": result_tone, "original_tone": tone})
    except Exception as e:
        return fail(str(e))


