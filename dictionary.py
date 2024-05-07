from readmdict import MDX
import re
import json
import concurrent.futures
import threading

print('正在加载词典文件,请稍候...')
mdxFileName = "8.mdx"

headwords = [*MDX(mdxFileName)]
items = [*MDX(mdxFileName).items()]
if len(headwords)==len(items):
    print(f'加载成功')
else:
    print(f'[error]加载失败')

# 不规则词, 专有名词字典懒得编, 我不高兴为80个专有名词或不规则动词或词性转换的词再浪费时间
with open("irregular_words.json", 'r') as file:
    irregular_words = json.load(file)

with open("dictionary.json", 'r') as file:
    dict_json = json.load(file)

def in_dict(word):
    return word in dict_json or word.encode() in headwords

def modify_word_helper(word, suffix):
    k = len(suffix)
    if in_dict(word[:-k] + 'e'):
        return word[:-k] + 'e'
    elif in_dict(word[:-k - 1] + 'y') and word[-k - 1] == 'i':
        return word[:-k - 1] + 'y'
    elif in_dict(word[:-k - 1]) and word[-k - 1] == word[-k - 2]:
        return word[:-k - 1]
    elif in_dict(word[:-k]):
        return word[:-k]
    return word + '?'

suffix_map = {
    'ing': lambda x: modify_word_helper(x, 'ing'),
    'ed': lambda x: modify_word_helper(x, 'ed'),
    'er': lambda x: modify_word_helper(x, 'er'),
    'est': lambda x: modify_word_helper(x, 'est'),
    'ly': lambda x: modify_word_helper(x, 'ly'),
    'ves': lambda x: x[:-3] + 'f' if x[:-3] + 'f' in headwords else x[:-3] + 'fe' if x[:-3] + 'fe' in headwords else x[:-3] + '?',
    'es': lambda x: modify_word_helper(x, 'es'),
    's': lambda x: modify_word_helper(x, 's')
}

def modify_word(word):
    if word in ["NAmE", "prep"]:
        return '?'
    word = word.lower()
    if in_dict(word):
        return word
    else:
        for suffix, handler in suffix_map.items():
            if word.endswith(suffix):
                return handler(word)
    if word in ["sb", "sth", "etc"]:
        return word
    elif word in irregular_words:
        return irregular_words[word]
    return word + '?'

punctuation = {',', '.', ';', ';', '/'}

def split_string(sentence):
    words = re.split(r"(\W+)", sentence)
    result = []
    first_word = True
    for item in words:
        if item.isalpha():
            word = modify_word(item)
            if '?' not in word: 
                result.append(word)
                first_word = False
            else:
                if item in ["prep", "adj", "NAmE", "adv"]:
                    continue
                for i in range(1, len(item)):
                    prefix, suffix = modify_word(item[:i]), modify_word(item[i:])
                    if '?' not in prefix and '?' not in suffix:
                        result.append(prefix)
                        result.append(suffix)
                        break
                if '?' in prefix or '?' in suffix:
                    result.append(word)
        elif first_word == False:
            if item == "." and result[-1] == "etc":
                continue
            if item in punctuation:
                result.append(item)
    return re.sub(r'\ \. \/ \.' ,'' ,' '.join(result))

chinese_and_brackets_pattern = re.compile(r'[\u4e00-\u9fff].*|\[.*?\]|\(.*?\)|/.{0,40}NAmE.{0,40}/')
clean_html_pattern = re.compile(r'<.*?>')
suffix_pattern = re.compile(r'SYN|☞|IDIOMS.*')
whitespace_pattern = re.compile(r'\s{2,}')
brace_pattern = re.compile(r'\(.*?\)')
part_of_speech_list = ["exclamation", "number", "suffix", "preposition", "article", "conjunction", "prefix",
                       "determiner", "abbreviation", "pronoun", "adverb", "noun", "verb", "adjective"]

# 短语, 习语, 部分数词不高兴搞, 我不高兴为23个单词浪费时间
def parse_text(word, input_text):
    if input_text.find('★') == -1:
        return None
    input_text = brace_pattern.sub(' ', whitespace_pattern.sub(' ', clean_html_pattern.sub('', input_text)))
    result = {}
    star_positions = [m.start() for m in re.finditer('★', input_text)]
    i, k = 1 if len(star_positions) > 1 else 0, None
    if (len(star_positions) < 4 and not input_text[star_positions[i] - 2].isdigit() and
        not any(any(input_text[star_positions[i] - len(pos_value) - 1: star_positions[i] - 1] == pos_value
        or input_text[star_positions[i] - len(pos_value) - 3: star_positions[i] - 3] == pos_value
        for i in range(len(star_positions))) for pos_value in part_of_speech_list)):
        i = 0
    positions = {}
    max_position, max_element = -1, None
    text = input_text[0: (star_positions[i] if input_text[star_positions[i] - 2].isdigit() else input_text.find('◆'))]
    for index, element in enumerate(part_of_speech_list):
        text_pos = text.rfind(element) + len(element)
        if element in text and text_pos > max_position:
            max_position, max_element = text_pos, element
    if max_element:
        k = 1 if input_text[star_positions[i] - 2].isdigit() else max_position if i == 0 else None
    while i < len(star_positions):
        for pos_value in part_of_speech_list:
            if i == 0:
                if max_element != pos_value:
                    continue
            elif input_text[star_positions[i] - len(pos_value) - 1: star_positions[i] - 1] == pos_value:
                k = 3
                if i + 1 < len(star_positions) and input_text[star_positions[i + 1] - 2].isdigit():
                    i += 1
                    k = 2
            elif input_text[star_positions[i] - len(pos_value) - 3: star_positions[i] - 3] == pos_value:
                k = 2
            if k == 1 and max_element != pos_value and (pos_value not in text or part_of_speech_list.index(pos_value) > 8):
                continue
            if k:
                definitions = []
                while i < len(star_positions) and (input_text[star_positions[i] - 2].isdigit() or k > 2):
                    l = star_positions[i] if k < 4 else k
                    j = l
                    while l < len(input_text) and input_text[l] != '◆' and not (input_text[l].isdigit() and input_text[l + 2] == '★'):
                        l += 1
                    text = chinese_and_brackets_pattern.sub(' ', input_text[j + 1: l - 1])
                    text = ''.join(char for char in text if ord(char) < 127)
                    text = suffix_pattern.sub('', text).lstrip()
                    text = re.sub(r'^' + word + r'(.{0,11}(sb|sth))'+ ('?' if pos_value in ["verb", "noun"] else ''), '', text)
                    text = split_string(text)
                    if len(text) > 2:
                        definitions.append(text)
                        result[pos_value] = definitions
                    i += 1
                    if k > 2:
                        break
                i -= 1
                k = None
                break
        i += 1;
    return result

all_results = {}
j = -1

while True:
    queryWord = input('查找：')
    if queryWord == 'q':
        break
    if queryWord.encode() not in headwords:
        print('未找到, 按q开始生成新的"dictionary.json". 重新', end='', flush=True)
        continue
    wordIndex = headwords.index(queryWord.encode())
    word,html = items[wordIndex]
    word,html = word.decode(), html.decode()
    result = parse_text(queryWord, html)
    print(json.dumps(result, ensure_ascii=False, indent=4))

def process_data(start_index, thread_id):
    for i in range(start_index, len(headwords), 8):
        queryWord = headwords[i].decode()
        word, html = items[i]
        word, html = word.decode(), html.decode()
        result = parse_text(queryWord, html)
        if result is not None:
            all_results[queryWord] = result
            text = '\r' + ' ' * 114 + f'\r线程{thread_id}: 已完成{int(i / len(headwords) * 1000)/10}%, 当前处理 {queryWord}'
            with threading.Lock():
                print(text, end='', flush=True)

with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
    futures = [executor.submit(process_data, i, thread_id) for thread_id, i in enumerate(range(0, 8))]
    for future in concurrent.futures.as_completed(futures):
        pass
    print('\r' + ' ' * 114 + "\r所有线程处理完毕")

all_results = {key: all_results[key] for key in sorted(all_results)}

filename = 'dictionary.json'
with open(filename, 'w', encoding='utf-8') as file:
    json.dump(all_results, file, ensure_ascii=False, indent=4)
