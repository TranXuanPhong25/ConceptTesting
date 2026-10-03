from tool import *
from collections import deque

def embedding(str, max_retries = 20, model = "text-embedding-ada-002"):
    
    with open('../config.json', 'r') as file:
        data = json.load(file)
    api_keys = data['api_keys']
    api_base = data['api_base']


    # for key in api_keys:
    attempts = 0
    completion = None
    while attempts < max_retries:
        key = random.choice(api_keys)
        # print("key:", key)
        try:
            openai.api_key = key
            openai.api_base = api_base
            completion = openai.Embedding.create(
                model=model,
                input=str
            )
            break
        except Exception as e:
            attempts += 1
            print(e)

            if attempts == max_retries:
                time.sleep(60)
                attempts = 0


    if not completion:
        return None

    output = completion["data"][0]["embedding"]
    return output


def extract_res_last_time(raw_llm):
    valid = 0
    res = None

    print("\n***** RES ANLAYSIS START *****")
    print("Raw LLM:")
    print(raw_llm)
    print("\n")

    msgs = []
    mutators = []

    # read the reponse
    try:
        data = json.loads(raw_llm)
    except Exception as e:
        msg = "Error parsing JSON: " + str(e) + " -> Directly output the JSON content without any additional output (e.g., no need for code delimiters like ```)."
        msgs.append(msg)

        return valid, msg

    

    for check in data.keys():

        check_info = {}
        for key, value in data[check].items():
            if "variable" in key.lower():
                check_info["variable"] = value
            elif "TORCH_CHECK" in key:
                check_info["TORCH_CHECK"] = value
            elif "requirement" in key.lower():
                check_info["Requirement"] = value

        print("-- check_info:", check_info)

        # check if "variable" and "Requirement" exist in the response
        if "variable" not in check_info.keys():
            msg = '''No related input variables is extracted. -> List the name and type of the related input variables (defined in the function header), and use comma to separate, such as "var1(type1), var2(type2)". If this TORCH_CHECK statement is not directly related to input variables, return 'None'.'''
            msgs.append(msg)
            continue
        
        if "Requirement" not in check_info.keys():
            msg = '''No requirement is extracted. -> whether the variables satisfy what requirements. Answer this question following "<the type> `<variable name>` should <requirement>", such as "the tensor input_t shuold be a 2D tensor". Note that variable names should be enclosed in backticks(``).'''
            msgs.append(msg)
            continue

        if check_info["variable"] == "None" and check_info["Requirement"] == "None":
            continue


        # check 1: check if the related input variables extracted from raw_llm is valid. Note that we skip the special case that the related input variables are none.
        ## output format: check if we can extract the corresponding results
        print("---- check variable")
        
        variables = check_info["variable"]
        vars_and_types = extract_vars_and_types(variables)
        if not vars_and_types:
            msg = '''You have not list the variables' names and types "The checked input variables" as required -> List the name and type of the related input variables (defined in the function header), and use comma to separate, such as "var1(type1), var2(type2)". If this TORCH_CHECK statement is not directly related to input variables, return 'None'.'''
            msgs.append(msg)
            continue

        print("------ vars_and_types:", vars_and_types)
        ## the types of input variables: check if these types in our 
        var_to_type = {}
        type_collection = []
        for var, type in vars_and_types:
            if type.lower() not in ["tensor", "int", "bool", "str", "float", "scalar", "list"]:
                msg = type + " is not considered -> Considering only the following variable types: {Tensor, Int, Bool, Str, Float, Scalar, List}. Otherwise, return 'None'."
                msgs.append(msg)
                continue

            tmp = type.lower()
            cnt = 1
            while tmp in type_collection:
                tmp = type.lower() + "_" + str(cnt)
                cnt += 1
            var_to_type[var] = tmp
            type_collection.append(tmp)

        print("------ var_to_type:", var_to_type)

        print("---- check Requirement")
        # check 2: check if the extracted requirements contain input variables in valid format
        check_requirement = check_info["Requirement"].lower()
        vars = re.findall(r'`([^`]+)`', check_requirement)
        if not vars:
            msg = '''The format of variables in the Requirement is not in the valid format -> Answer this question following "`<variable name>` should <requirement>", such as "the `input_t` shuold be a 2D tensor". Note that variable names should be enclosed in backticks(``).'''
            continue
        vars = list(set(vars))
        types = []
        for var in vars:
            if var not in var_to_type.keys():
                msg = "The variables used in 'Requirement' is not compatible with the 'The checked input variables' -> Please check the 'Requirement' and the 'The checked input variables'."
                continue
            types.append(var_to_type[var])
            check_requirement = check_requirement.replace("`" + var + "`", "`" + var_to_type[var] + "`")
        
        mutators.append({"types": types, "mutator": check_requirement})
            

        # types = extract_types(check_info["Requirement"].lower())
        # print("------ types:", types)
        # save_flag = True
        # for type in types:
        #     if type.lower() not in ["tensor", "int", "bool", "str", "float", "scalar", "list"]:
        #         save_flag = False

        # if save_flag and types:
        #     mutator = remove_backticks(check_info["Requirement"])
        #     mutators.append({"types": types, "mutator": mutator})
        # else:
        #     msg = '''The format of requirement `{requirement}` is not valid. -> Answer this question following "<the type> `<variable name>` should <requirement>", such as "the tensor input_t shuold be a 2D tensor". Note that variable names should be enclosed in backticks(``).'''
        #     msgs.append(msg)
        #     return 0, msg

    print("msgs:", msgs)
    print("mutators:", mutators)

    print("***** RES ANLAYSIS END *****\n")

    return 1, mutators


Q_template = """```
the `int` should be greater than or equal to 6
```
Based on the relationships indicated by 'and/or', divide the aforementioned condition into distinct parts. If the above condition does not have "and/or" relationships, simply summarize the condition. Output the results following "<num>. <sub-requirement>"""

A_template = """1. The `int` should be greater than 6.
2. The `int` should be equal to 6."""

prompt_template = """```
<TARGET_MUTATOR>
```
Based on the relationships indicated by 'and/or', divide the aforementioned condition into distinct parts. If the above condition does not have "and/or" relationships, simply summarize the condition. Output the results following "<num>. <sub-requirement>"""




messages_template = [
    {"role": "system", "content": "You are a LLM."},
    {"role": "user", "content": Q_template},
    {"role": "assistant", "content": A_template},
    {"role": "user", "content": ""}
]

def construct_message(mutator):
    prompt = prompt_template.replace("<TARGET_MUTATOR>", mutator)

    messages = copy.deepcopy(messages_template)
    messages[-1]["content"] = prompt

    
    return messages

def extract_mutator(text):
    pattern = r'\d+\.\s*(.*)'
    matches = re.findall(pattern, text, flags=re.MULTILINE)

    res = []
    for info in matches:
        res.append(info.strip())

    if res:
        return res, 1
    else:
        msg = '''Output the results following "<num>. <sub-requirement>", such as "1. The `int` should be greater than 6.".'''
        return msg, 0

def decompose_element(init_mutaotr, decompose_res):
    print("\n======== decompose start ========")

    decomposition_result = []
    queue = deque([init_mutaotr])
    
    while queue:
        print("\nqueue:", queue)

        current_element = queue.popleft()
        print("current_element:", current_element)
        
        # construct message
        message = construct_message(current_element)
        
        res, valid = reask(message, extract_mutator, 5)
        print("res:", res)

        if not valid:
            decomposition_result.append(current_element)
            continue

        if len(res) == 1:
            decomposition_result.append(res)
            continue
        else:
            queue.extend(res)

    print("\norigin:", init_mutaotr)
    print("decomposition_result:", decomposition_result)
    decompose_res[init_mutaotr] = decomposition_result

    print("======== decompose end ========\n")
    
    return decomposition_result


Q_template_1 = """The set of conditions = ```1. the `tensor` tensor should be contiguous
2. the `tensor` should be nested
3. the `tensor` should have a dimension of 4 or 5
```

Among the above conditions, are there any items that have the same constraints as "the `tensor` should be 4d"? Answer `Yes` or `No`. The answer should be enclosed in backticks(``), such as `Yes/No`."""

A_template_1 = """Task 1: The item that has the same constraints as "the `tensor` should be 4d" is: "the tensor should have a dimension of 4 or 5".
Task 2: `Yes`"""

Q_template_2 = """The set of conditions = ```1. the `tensor` tensor should be contiguous
2. the `tensor` should be nested
3. the `tensor` should have a dimension of 4 or 5
```

Among the above conditions, are there any items that have the same constraints as "the `tensor` should be 7d"? Answer `Yes` or `No`. The answer should be enclosed in backticks(``), such as `Yes/No`."""

A_template_2 = """Task 1: there are no items that have the same constraints as "the `tensor` should be 7d".
Task 2: `No`"""

prompt_template = """
<UNIQUE_SET>
```

Among the above conditions, are there any items that have the same constraints as "MUTATOR"? Answer `Yes` or `No`. The answer should be enclosed in backticks(``), such as `Yes/No`."""

messages_template = [
    {"role": "system", "content": "You are a LLM."},
    {"role": "user", "content": Q_template_1},
    {"role": "assistant", "content": A_template_1},
    {"role": "user", "content": Q_template_2},
    {"role": "assistant", "content": A_template_2},
    {"role": "user", "content": ""}
]

verify_Q = """Is the constraint of "the `tensor` should be contiguous" the same as the constraint of "the `tensor` should be a non-empty 3d data tensor? Answer `Yes` or `No` and give the reason. The answer should be enclosed in backticks(``), such as `Yes/No`."""

verify_A = """`No`, these constraints are not the same.
1. "The tensor should be contiguous": This constraint refers to the memory layout of the tensor, as explained earlier. It means that the elements of the tensor are stored in a single, contiguous block of memory without any gaps or extra padding between them. This is typically a requirement for certain operations or optimizations in frameworks like PyTorch or TensorFlow.
2. "The tensor should be a non-empty 3D data tensor": This constraint specifies the shape and content of the tensor. It indicates that the tensor should have three dimensions (e.g., width, height, and depth in the case of image data), and it should contain actual data (i.e., not be empty). This constraint doesn't directly relate to the memory layout; rather, it concerns the structure and content of the tensor.
"""

verify_prompt_template = """Is the constraint of "MUTATOR_1" the same as the constraint of "MUTATOR_2"? Answer `Yes` or `No` and give the reason. The answer should be enclosed in backticks(``), such as `Yes/No`."""

verify_template = [
    {"role": "system", "content": "You are a LLM."},
    {"role": "user", "content": verify_Q},
    {"role": "assistant", "content": verify_A},
    {"role": "user", "content": ""}
]

prompt_template = """
```
<UNIQUE_SET>
```

Among the above conditions, are there any items that have the same constraints as "MUTATOR"? If exists, return the item that has the same constraints by enclosing in "{ }", such as {a condition}.
"""

messages_template = [
    {"role": "system", "content": "You are a coding expert."},
    {"role": "user", "content": ""}
]

def extract_res(raw_llm, mutator):
    pattern = r'\{([^{}]*)\}'
    matches = re.findall(pattern, raw_llm)
    if len(matches) == 0:
        return "non-existent", 1
    elif len(matches) == 1:
        if matches[0] == "" or matches[0].lower() == "none":
            return "non-existent", 1
    
    return matches[0], 1

def extract_res_verify(raw_llm, mutator):
    if "`yes`" in raw_llm.lower():
        return True, 1
    elif "`no`" in raw_llm.lower():
        return False, 1
    else:
        msg = "Answer `Yes` or `No` and give the reason. The answer should be enclosed in backticks(``), such as `Yes/No`."
        return msg, 0

def verify(mutator_1, mutator_2):
    print("----- verify start -----")
    # construct prompt
    prompt = verify_prompt_template.replace("MUTATOR_1", mutator_1)
    prompt = prompt.replace("MUTATOR_2", mutator_2)

    messages = copy.deepcopy(verify_template)
    messages[-1]["content"] = prompt

    # ask LLM
    res, valid = reask(messages, extract_res_verify, 3, "")

    print("----- verify end -----")
    if valid:
        return res
    else:
        return None


Q = """
```
the tensor should be a 1d tensor
the tensor should be a tensor on a cpu or cuda device
the tensor should have floating point or complex dtype
the tensor should be a 2d tensor
the tensor should have at least one dimension
the tensor should have more than 0 elements
the tensor should have at least 2 dimensions
```

Find a set of (tensor) that would violate all the above conditions simultaneously. The description of the (tensor): tensor refers to a data type of tensor.

Answer this question following these steps: 
Step I. Analyze each condition.
Step II. Create a set of (tensor) that violates all conditions simultaneously: "<num>. <The requirements of the (tensor)> (violates conditions X)".
Step II. Output the results in json format:
```json
{
	"index": {
		"data": "", # the description of the (tensor), such as "the (tensor) should be ..."
		"violate": "" # this (tensor) violates which conditions
	}
}
```
"""

A = """Step I. Analyze each condition:
1. 1d tensor: This condition is violated by tensors with more than one dimension.
2. Tensor on a CPU or CUDA device: We can create tensors on different devices to violate this condition.
3. Floating point or complex dtype: Tensors with other dtypes would violate this condition.
4. 2d tensor: This condition is violated by tensors with fewer or more than two dimensions.
5. At least one dimension: Tensors with zero dimensions (scalars) violate this condition.
6. More than 0 elements: Tensors with zero elements (empty tensors) violate this condition.
7. At least 2 dimensions: This condition is violated by tensors with fewer than two dimensions.

Step II. Create a set of tensors that violates all conditions simultaneously:
1. A scalar tensor with an integer dtype (violates conditions 1, 3, 4, 5, 6, and 7).
2. An empty tensor (zero elements) with any valid dtype (violates conditions 1, 2, 4, and 6).
3. A scalar tensor on a non-CPU/CUDA device (violates conditions 2, 3, 4, 5, 6, and 7).

Step III. Output:
```json
{
	"1": {
		"data": "A scalar tensor with an integer dtype",
		"violate": "violates conditions 1, 3, 4, 5, 6, and 7"
	}, 
	"2": {
		"data": "An empty tensor (zero elements) with any valid dtype",
		"violate": "violates conditions 1, 2, 4, and 6"
	}, 
	"3": {
		"data": "A scalar tensor on a non-CPU/CUDA device",
		"violate": "violates conditions 2, 3, 4, 5, 6, and 7"
	}, 
}
```"""

prompt_template = """
```
<MUTATORS>
```

Create a set of <DATA> that violate all conditions. Each condition will be violated by one/multiple <DATA>. <DESCRIPTION>

Output the results in JSON format:
```json
[
	{
		"data-description": "", # the description of the <DATA>
		"violated conditions": "" # the description of the conditions that this <DATA> violates, such as [CON_EXAMPLE]
	}
]
```

Directly output the JSON content without any additional output (e.g., no need for code delimiters like ```).
"""

messages_template = [
    {"role": "system", "content": "You are a LLM."},
    {"role": "user", "content": ""}
]

def var_replace(var):
    template = "SOURCE refers to a data type of TARGET. "
    if "tensor" in var:
        return template.replace("TARGET", "tensor").replace("SOURCE", var)
    elif "int" in var:
        return template.replace("TARGET", "int").replace("SOURCE", var)
    elif "bool" in var:
        return template.replace("TARGET", "bool").replace("SOURCE", var)
    elif "str" in var:
        return template.replace("TARGET", "str").replace("SOURCE", var)
    elif "float" in var:
        return template.replace("TARGET", "float").replace("SOURCE", var)
    elif "scalar" in var:
        return template.replace("TARGET", "scalar").replace("SOURCE", var)
    elif "list" in var:
        return template.replace("TARGET", "list").replace("SOURCE", var)

def read_mutators(filename):
    with open(filename, 'r') as f:
        data = json.load(f)

    all_mutators_unique = []
    for pattern in data:
        type_pattern = pattern["types"]
        mutator = pattern["mutator"]

        if not type_pattern:
            continue

        repeated = 0
        for unique_pattern in all_mutators_unique:
            type_pattern_unique = unique_pattern["types"]
            mutator_unique = unique_pattern["mutator"]
            if set(type_pattern_unique) == set(type_pattern) and mutator_unique == mutator:
                repeated = 1
                break
        
        if repeated == 0:
            all_mutators_unique.append(pattern)

    all_mutators_dict = {}
    pattern_description = {}

    for pattern in all_mutators_unique:
        type_pattern = sorted(pattern["types"])
        mutator = pattern["mutator"]

        res = "The description of the " + str(type_pattern).replace("'", "") + " is: "
        for var in type_pattern:
            res += var_replace(var)
        pattern_description[str(type_pattern)] = res

        if str(type_pattern) not in all_mutators_dict.keys():
            all_mutators_dict[str(type_pattern)] = []
        all_mutators_dict[str(type_pattern)].append(mutator)
    
    return all_mutators_dict, pattern_description

def extract_code(text):
    try:
        dataset = json.loads(text)
        violated_state = []
        for data in dataset:
            violated_state.append(data['violated conditions'])
        print("violated_state:", violated_state)
        target_idx = min_subset_cover_indices(violated_state)
        print("target_idx:", target_idx)

        mutators = []
        for idx in target_idx:
            mutators.append(dataset[idx]['data-description'])
        
        print("mutators:", mutators)
        return mutators, ""
            
    except Exception as e:
        msg = "Directly output the JSON content without any additional output (e.g., no need for code delimiters like ```)."
        return None, msg

def min_subset_cover_indices(B):
    A = []
    for tmp in B:
        A.extend(tmp)
    A = set(A)

    B = [set(b) for b in B]  # Convert each list in B to a set
    cover_indices = []  # Initialize the list for indices of the cover
    original_B = list(B)  # Make a copy of B to remember original indices

    while A:  # While there are elements left to cover in A
        # Find the set in B that covers the most elements in A
        max_set = max(B, key=lambda s: len(s & A))
        cover_indices.append(original_B.index(max_set))  # Add the index of the found set
        A -= max_set  # Remove the covered elements from A
        B.remove(max_set)  # Remove the used set from B

        # Clean up B by removing sets that are now redundant
        B = [b for b in B if not b.issubset(max_set)]

    return cover_indices

def reask(dialog, extract_code, MAX_TRY):
    SUCCESS = 0
    try_cnt = 0
    while try_cnt < MAX_TRY:
        # print("\ntry_cnt:", try_cnt)
        print(dialog)
        # raw_llm = request_openai_api(dialog, 20, model = "GPT-4")
        raw_llm = request_openai_api(dialog, 20)
        print("raw_llm:", raw_llm)

        code, msg = extract_code(raw_llm) 
        print("code:", code)
        print("msg:", msg)

        if code:
            SUCCESS = 1
            break
        else:
            dialog.append(
                {"role": "assistant", "content": raw_llm}
            )
            dialog.append(
                {"role": "user", "content": msg + " Please generate again."}
            )
            print(msg)

        try_cnt += 1

    
    if SUCCESS:
        return code, 1
    else:
        print("---- Can not finish this task. Here are the unsloved problem:", msg)
        return None, 0
    


def analysis(groups, type_pattern, description):
    # construct prompt
    result = ""
    for i, item in enumerate(groups, start=1):
        result += f"{i}. {item}\n"
    prompt = prompt_template.replace("<MUTATORS>", result)
    prompt = prompt.replace("<DATA>", type_pattern)
    prompt = prompt.replace("<DESCRIPTION>", description)

    con_str = "\"" + groups[0] + "\", "
    if len(groups) > 1:
        con_str += "\"" + groups[1] + "\""
    prompt = prompt.replace("CON_EXAMPLE", con_str)

    print("\n--- prompt start ---")
    print(prompt)
    print("--- prompt end ---\n")

    messages = copy.deepcopy(messages_template)
    messages[-1]["content"] = prompt

    # ask LLM
    res, valid = reask(messages, extract_code, 3)
    if valid:
        return res
    else:
        return None
    


from sklearn.cluster import KMeans
def cluster(vectors, n_clusters, sentences):
    kmeans = KMeans(n_clusters=n_clusters)
    kmeans.fit(vectors)
    labels = kmeans.labels_

    print(labels)

    clustered_sentences = {}

    for i, label in enumerate(labels):
        if label not in clustered_sentences:
            clustered_sentences[label] = [sentences[i]]
        else:
            clustered_sentences[label].append(sentences[i])

    return clustered_sentences

if __name__ == "__main__":
    filename = "all_mutators.json"
    res_name = "unique_mutators.json"

    if os.path.exists(res_name):
        with open(res_name, 'r') as json_file:
            unique_mutators = json.load(json_file)

            # for ori, res in decompose_res.items():
            #     print("ori:", ori)
            #     print("res:", res, "\n")
    else:
        unique_mutators = {}
    
    all_mutators_dict, pattern_description = read_mutators(filename)
    
    print("===== Cluster Start =====")
    all_clusters = {}
    cluster_name = "all_clusters.json"
    if os.path.exists(cluster_name):
        with open(cluster_name, 'r') as json_file:
            all_clusters = json.load(json_file)

    for type_pattern, mutators in all_mutators_dict.items():
        print("\n\ntype_pattern:", type_pattern)
        if type_pattern in all_clusters.keys():
            print(type_pattern, "has been analyzed.")
            continue

        print("num:", len(mutators))
        all_clusters[type_pattern] = []

        if len(mutators) > 5:
            n_clusters = int(len(mutators)/5) + 1
            print("n_clusters:", n_clusters)

            vectors = []
            for mutator in mutators:
                print(mutator)
                vector = embedding(mutator)
                vectors.append(vector)
            print("\n")

            print(len(vectors))
            for vec in vectors:
                print(len(vec))

            clustered_sentences = cluster(vectors, n_clusters, mutators)

            for cluster_idx, sentences_in_cluster in clustered_sentences.items():
                all_clusters[type_pattern].append(sentences_in_cluster)
                print("Cluster", cluster_idx, ":")
                for sentence in sentences_in_cluster:
                    print("-", sentence)
        else:
            all_clusters[type_pattern].append(mutators)
            print("do not need to be clustered")
        
        with open(cluster_name, 'w') as json_file:
            json.dump(all_clusters, json_file)

    print("all_clusters:", all_clusters)

    print("===== Cluster End =====")