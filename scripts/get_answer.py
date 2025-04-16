import os
import sys
import json
import tqdm
import openai
import argparse
from string import Template
from dotenv import load_dotenv
from concurrent.futures import ProcessPoolExecutor

choice_number = 5
temperature = 0.2

scripts_dir = sys.path[0]
project_dir = os.path.abspath(os.path.join(scripts_dir, ".."))
questions_dir = os.path.join(project_dir, "dataset")
results_dir = os.path.join(project_dir, "results")
config_dir = os.path.join(project_dir, "config")

load_dotenv(os.path.join(config_dir, ".env"))

client = openai.OpenAI(
    api_key=os.environ.get("OPENAI_API_KEY")
)

def generateAnswers(args):
    question, model, prompt_type, correct_answer = args

    if prompt_type == "few-shot":
        prompt_template = Template("""
Here is a multipul choice question (with answers) about Computer and Security Knowledge.

## Instruction
There is only one answer to the question, please return the result directly (A/B/C/D) without adding any other content.

## Example input 1
Question: This is a question about Data_Storage_Size. The term gigabyte refers to
A. 1024 bytes
B. 1024 megabytes
C. 1024 kilobytes
D. 1024 gigabyte

## Example output 1
B

## Example input 2
Question: This is a question about Programming_Languages. Machine language is
A. Machine dependent
B. Difficult to program
C. Error prone
D. All of above

## Example output 2
D

## Example input 3
Question: This is a question about Data_Storage_Units. A byte consists of
A. One bit
B. Four bits
C. Eight bits
D. Sixteen bits

## Example output 3
C

## Example input 4
Question: This is a question about Data_Representation. What is the date when Babbage conceived Analytical engine?
A. 1642
B. 1837
C. 1880
D. 1850

## Example output 4
C

## Example input 5
Question: This is a question about Programming_Language_Levels. Which of the following is a machine-independent program?
A. High level language
B. Low level language
C. Assembly language
D. Machine language

## Example output 5
A

## Input
Question: $question                                      

## Output

""")
    else:
        prompt_template = Template("""
Here is a multipul choice question (with answers) about Computer and Security Knowledge.

Question: $question

## Instruction
There is only one answer to the question, please return the result directly (A/B/C/D) without adding any other content.
"""
    )
    prompt = Template.substitute(prompt_template, question=question)
    if prompt_type == "cot":
        prompt = prompt.replace("without adding any other content.", "at the end of your response. Let's think step by step.")

    response = client.chat.completions.create(
        messages=[
            {
                "role": "user",
                "content": prompt,
            }
        ],
        model=model,
        temperature=temperature,
        n=choice_number
    )

    results = []
    for res in response.choices:
        results.append({
            "model_name": model,
            "key_answer_type": "alphabet_option",
            "question": question,
            "llm_output": res.message.content,
            "correct_answer": correct_answer,
            "standard_answer_range": [[choice[:1], choice[3:]] for choice in question.split("\n")[1:]]
        })
    return results

# Function to reformat questions
def reformat_questions(json_data):
    reformatted_questions = []
    for key in json_data:
        for item in json_data[key]["questions"]:
            question_text = f'This is a question about {key.split(".")[-1].replace("_slash_", "/").replace("_", " ")}. {item["question"]}'
            choices = item['choices']
            reformatted_question = f"{question_text}"
            for i in range(len(choices)):
                label = "ABCDEFGHI"[i]
                reformatted_question += f"\n{label}. {choices[i]}"
            
            reformatted_questions.append(reformatted_question)
    
    return reformatted_questions

if __name__ == "__main__":
    
    parser = argparse.ArgumentParser(description="Script to get answers from LLMs.")
    parser.add_argument('--model', type=str, required=True, help="Specify the model to use, e.g., gpt-3.5-turbo")
    parser.add_argument('--worker', type=int, required=True, help="Specify the max worker model to use")

    args = parser.parse_args()
    
    model = args.model
    num_worker = args.worker

    for prompt_type in ["zero-shot", "few-shot", "cot"]:
        for i in ["A", "B", "C", "D"]:
            with open(os.path.join(questions_dir, f"csebench_{i}.json"), "r") as f:
                json_data = json.loads(f.read())

            print(f"[*] Processing distribution {i} of {prompt_type} ...")

            reformatted_questions = reformat_questions(json_data)

            args_list = []
            for question in reformatted_questions:
                args_list.append((question, model, prompt_type, i))

            results = []

            with ProcessPoolExecutor(max_workers=num_worker) as executor:
                results = list(tqdm.tqdm(executor.map(generateAnswers, args_list), total=len(args_list)))

            ret_results = []
            for res in results:
                ret_results += res

            if not os.path.exists(results_dir):
                os.makedirs(results_dir)

            output_path = os.path.join(results_dir, f"results_{model}_{prompt_type}_{i}.json")
            with open(output_path, 'w', encoding='utf-8') as output:
                json.dump(ret_results, output, ensure_ascii=False, indent=4)

            print(f"[OK] Results saved to {output_path}")