import json

with open('dictionary.json', 'r') as file:
    dictionary = json.load(file)

pos_to_file = {
    "noun": "noun.json",
    "verb": "verb.json",
    "adjective": "adjective.json",
    "adverb": "adverb.json",
    "conjunction": "conjunction.json",
    "preposition": "preposition.json"
}

for pos in pos_to_file:
    pos_definitions = {}
    for word, definitions in dictionary.items():
        if pos in definitions:
            pos_definitions[word] = definitions[pos]
    
    with open(pos_to_file[pos], 'w') as file:
        json.dump(pos_definitions, file, indent=4)
    
    print(f"词性 {pos} 的定义已提取并保存到 {pos_to_file[pos]} 文件中。")
