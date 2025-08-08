import json
import os
import re
import ast
from functools import lru_cache
from typing import Tuple, List, Dict, Any, Optional

import pandas as pd
from flask import current_app


def build_tone_dict(rhymebook_data: List[Dict[str, Any]]) -> Tuple[Dict[str, str], Dict[str, List[str]]]:
    tone_dict: Dict[str, str] = {}
    yunbu_dict: Dict[str, set] = {}
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
    yunbu_dict_list: Dict[str, List[str]] = {k: list(v) for k, v in yunbu_dict.items()}
    return tone_dict, yunbu_dict_list


@lru_cache(maxsize=8)
def load_rhymebook_with_yunbu(rhymebook_choice: str) -> Tuple[Dict[str, str], Dict[str, List[str]]]:
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


@lru_cache(maxsize=1)
def load_cipai() -> pd.DataFrame:
    cipai_path = 'data/cipai_with_statistics_qdcp.csv'
    if not os.path.exists(cipai_path):
        raise FileNotFoundError(f"词牌谱文件未找到: {cipai_path}")
    df = pd.read_csv(cipai_path)
    df['词牌名'] = df['词牌名'].astype(str).str.strip()
    df['作者'] = df['作者'].astype(str).str.strip()
    return df


@lru_cache(maxsize=1)
def load_cipai_intro() -> Dict[str, str]:
    intro_path = 'data/cipai_detail_with_intro.csv'
    intro_dict: Dict[str, str] = {}
    if not os.path.exists(intro_path):
        return intro_dict
    df = pd.read_csv(intro_path)
    df['词牌名'] = df['词牌名'].astype(str).str.strip()
    for _, row in df.iterrows():
        intro_dict[str(row['词牌名']).strip()] = str(row['介绍']).strip()
    return intro_dict


@lru_cache(maxsize=2)
def load_yunjiao(filepath: str = 'data/yunjiao.csv') -> Dict[str, List[List[int]]]:
    yunjiao_dict: Dict[str, List[List[int]]] = {}
    df = pd.read_csv(filepath)
    for _, row in df.iterrows():
        cipai_name = str(row['词牌名']).strip()
        author = str(row['作者']).strip()
        key = f"{cipai_name}|{author}"
        yunjiao_str = str(row['韵脚']).strip()
        if yunjiao_str.startswith('"') and yunjiao_str.endswith('"'):
            yunjiao_str = yunjiao_str[1:-1]
        try:
            positions = json.loads(yunjiao_str)
            if key in yunjiao_dict:
                if positions not in yunjiao_dict[key]:
                    yunjiao_dict[key].append(positions)
            else:
                yunjiao_dict[key] = [positions]
        except Exception:
            continue
    return yunjiao_dict


@lru_cache(maxsize=1)
def get_cipai_summary_list() -> Tuple[List[Dict[str, Any]], int]:
    """构建去重排序后的词牌列表，并缓存结果。

    返回 (cipai_list, default_index)
    """
    cipai_data = load_cipai()

    cipai_list: List[Dict[str, Any]] = []
    seen = set()

    for _, row in cipai_data.iterrows():
        cipai_name = str(row['词牌名']).strip()
        author = str(row['作者']).strip()
        total_chars = int(row['总数'])
        split_length = row['分段字数']

        key = f"{cipai_name}|{author}|{total_chars}"
        if key in seen:
            continue
        seen.add(key)

        cipai_list.append({
            "cipai_name": cipai_name,
            "author": author,
            "total_chars": total_chars,
            "split_length": split_length,
            "display_name": f"{cipai_name} - {author} ({total_chars}字)",
        })

    cipai_list.sort(key=lambda x: (x['cipai_name'], x['total_chars']))

    default_index = 0
    for i, item in enumerate(cipai_list):
        if item['cipai_name'] == '竹枝' and item['author'] == '皇甫松' and item['total_chars'] == 14:
            default_index = i
            break

    return cipai_list, default_index


def preprocess_text(text: str) -> Tuple[str, str, int, List[int]]:
    text_cleaned = re.sub(r'\s+', '', text)
    text_drop = re.sub("[^\u4e00-\u9fa5]", "", text_cleaned)
    length = len(text_drop)
    sentences = re.split('[，。、？！]', text_cleaned)
    split_length = [len(re.sub("[^\u4e00-\u9fa5]", "", sentence)) for sentence in sentences if sentence.strip()]
    return text_drop, text_cleaned, length, split_length


def guess_cipai_name(length: int, split_length: List[int], cipai_data: pd.DataFrame) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    for row in cipai_data.itertuples():
        try:
            if length == getattr(row, '总数') and str(split_length) == getattr(row, '分段字数'):
                return getattr(row, '词牌名'), getattr(row, '作者'), getattr(row, '韵律')
        except Exception:
            continue
    return None, None, None


def mark_tone(text: str, tone_dict: Dict[str, str]) -> List[Tuple[str, str]]:
    tone_text: List[Tuple[str, str]] = []
    for word in text:
        tone_text.append((word, tone_dict.get(word, '未知')))
    return tone_text


def get_score_tone(tone_text: List[Tuple[str, str]], tone_database: List[str]) -> Tuple[float, List[Tuple[Tuple[str, str], str, int]]]:
    score = 0
    issue_data: List[Tuple[Tuple[str, str], str, int]] = []
    for index, (item1, item2) in enumerate(zip(tone_text, tone_database)):
        if item1[1] != item2 and item2 != '中':
            issue_data.append((item1, item2, index))
        elif item1[1] == item2 or item2 == '中':
            score += 1
    total = len(tone_database)
    score_percent = (score / total * 100) if total else 0
    return score_percent, issue_data


def estimate_poetry(text: str, rhymebook: str) -> Dict[str, Any]:
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
    except Exception:
        cipai_intro_dict = {}

    text_drop, text_cleaned, length, split_length = preprocess_text(text)
    guess_cipai, author, tone_database = guess_cipai_name(length, split_length, cipai_data)

    if not tone_database:
        # Log for debugging when no matching cipai is found
        try:
            current_app.logger.info(
                f"Cipai match failed. total_chars={length}, split_length={split_length}"
            )
        except Exception:
            pass
        return {
            "success": False,
            "message": "未能匹配到词牌名，请检查输入文本或词牌谱数据。",
            "text": text,
            "processed_text": text_drop,
            "length": length,
            "split_length": split_length
        }

    tone_database = re.sub("[^\u4e00-\u9fa5]", "", tone_database)
    tone_database = list(re.sub(r"增韵", "", tone_database))
    tone_text = mark_tone(text_drop, tone_dict)
    score, issue_data = get_score_tone(tone_text, tone_database)

    yunjiao_options: List[Dict[str, Any]] = []
    yunjiao_words: List[str] = []
    yunjiao_yunbu: Dict[str, List[str]] = {}
    yunjiao_detailed: List[Dict[str, Any]] = []

    if guess_cipai and author:
        key = f"{guess_cipai.strip()}|{author.strip()}"
        yunjiao_patterns = yunjiao_dict.get(key, [])
        if yunjiao_patterns:
            text_drop_to_original_map: Dict[int, int] = {}
            text_drop_index = 0
            for original_index, char in enumerate(text_cleaned):
                if re.match(r'[\u4e00-\u9fa5]', char):
                    text_drop_to_original_map[text_drop_index] = original_index
                    text_drop_index += 1

            for i, positions in enumerate(yunjiao_patterns):
                pattern_words = [text_drop[pos - 1] for pos in positions if 0 < pos <= len(text_drop)]
                pattern_detailed = []
                pattern_yunbu: Dict[str, List[str]] = {}
                for pos in positions:
                    if 0 < pos <= len(text_drop):
                        word = text_drop[pos - 1]
                        text_drop_pos = pos - 1
                        original_pos = text_drop_to_original_map.get(text_drop_pos, -1)
                        if original_pos >= 0:
                            yunbu_list = [yunbu for yunbu, words in yunbu_dict.items() if word in words]
                            pattern_detailed.append({
                                "position": original_pos,
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

            if yunjiao_options:
                first_option = yunjiao_options[0]
                yunjiao_words = first_option["words"]
                yunjiao_yunbu = first_option["yunbu"]
                yunjiao_detailed = first_option["detailed"]

    cipai_intro = ""
    if guess_cipai and cipai_intro_dict:
        cipai_intro = cipai_intro_dict.get(guess_cipai.strip(), "")

    return {
        "success": True,
        "text": text_cleaned,
        "original_text": text,
        "processed_text": text_drop,
        "cipai_name": guess_cipai,
        "cipai_intro": cipai_intro,
        "author": author,
        "score": round(score, 2),
        "issues": [
            {"word": w, "actual": a, "expected": e, "position": p}
            for (w, a), e, p in issue_data
        ],
        "yunjiao_words": yunjiao_words,
        "yunjiao_yunbu": yunjiao_yunbu,
        "yunjiao_detailed": yunjiao_detailed,
        "yunjiao_options": yunjiao_options,
        "tone_text": tone_text,
        "length": length,
        "split_length": split_length,
    }


def create_fillword_framework(tone_pattern: List[str], split_length: List[int]) -> Dict[str, Any]:
    if not split_length:
        total_length = len(tone_pattern)
        split_length = [total_length // 2, total_length - total_length // 2]

    total_length = len(tone_pattern)
    mid_point = total_length // 2

    current_pos = 0
    shangque_end = mid_point
    for length in split_length:
        if current_pos + length >= mid_point:
            shangque_end = current_pos + length
            break
        current_pos += length

    ques = []
    shangque_tones = tone_pattern[:shangque_end]
    shangque_sentences = create_sentences_from_split_length(shangque_tones, split_length[:get_segments_count_for_length(split_length, shangque_end)])
    ques.append({"name": "上阕", "length": len(shangque_tones), "sentences": shangque_sentences})

    xiaque_tones = tone_pattern[shangque_end:]
    remaining_splits = split_length[get_segments_count_for_length(split_length, shangque_end):]
    xiaque_sentences = create_sentences_from_split_length(xiaque_tones, remaining_splits)
    ques.append({"name": "下阕", "length": len(xiaque_tones), "sentences": xiaque_sentences})

    return {"ques": ques, "total_chars": len(tone_pattern)}


def get_segments_count_for_length(split_length: List[int], target_length: int) -> int:
    current_length = 0
    for i, length in enumerate(split_length):
        current_length += length
        if current_length >= target_length:
            return i + 1
    return len(split_length)


def create_sentences_from_split_length(tones: List[str], split_lengths: List[int]) -> List[List[str]]:
    sentences: List[List[str]] = []
    current_pos = 0
    for length in split_lengths:
        if current_pos >= len(tones):
            break
        sentence = tones[current_pos:current_pos + length]
        if sentence:
            sentences.append(sentence)
        current_pos += length
    return sentences


