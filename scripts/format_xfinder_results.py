import re
import os
import sys
import json

scripts_dir = sys.path[0]
project_dir = os.path.abspath(os.path.join(scripts_dir, ".."))
questions_dir = os.path.join(project_dir, "dataset")
results_dir = os.path.join(project_dir, "results")

def get_xfinder_answer(answer):
    results_re = re.findall(r'\bKey extracted answer: assistant\n\n([A-D])$', answer)
    if len(results_re) == 1:
        return results_re[0]
    results_re = re.findall(r'\bKey extracted answer: assistant\n\n([A-D])\. .*?$', answer)
    if len(results_re) == 1:
        return results_re[0]
    results_re = re.findall(r'\bKey extracted answer: assistant\n\n([A-D])\.$', answer)
    if len(results_re) == 1:
        return results_re[0]
    else:
        return "X"

if __name__ == '__main__':

    for root, dirs, files in os.walk(results_dir):
        for file in files:
            if not file.endswith("_xfinder.json"):
                continue
            
            with open(os.path.join(root, file), "r", encoding="utf-8") as f:
                data = json.loads(f.read())
            
            qa_dict = {}
            for xfinder_item in data:
                question = xfinder_item['question']
                if question not in qa_dict:
                    qa_dict[question] = []
                qa_dict[question].append(get_xfinder_answer(xfinder_item['correct_answer']))
            
            result_data = {}
            for question in qa_dict:
                if len(qa_dict[question]) != 5:
                    print(f"[x] Incorrect answer number: {question}")
                    exit(1)
                
                result_data.append({
                    "question": question,
                    "answers": qa_dict[question]
                })

            with open(os.path.join(results_dir, file.replace("_xfinder", "_final")), "w", encoding="utf-8") as f:
                f.write(json.dumps(result_data, ensure_ascii=False, indent=4))