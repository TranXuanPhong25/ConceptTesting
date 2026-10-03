from tool import *

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

            cnt = 1
            tmp = type.lower() + "_" + str(cnt)
            
            while tmp in type_collection:
                cnt += 1
                tmp = type.lower() + "_" + str(cnt)

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

def extract_res(raw_llm):
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
            return 0, msg
        
        if "Requirement" not in check_info.keys():
            msg = '''No requirement is extracted. -> whether the variables satisfy what requirements. Answer this question following "<the type> `<variable name>` should <requirement>", such as "the tensor input_t shuold be a 2D tensor". Note that variable names should be enclosed in backticks(``).'''
            msgs.append(msg)
            return 0, msg

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
            return 0, msg

        print("------ vars_and_types:", vars_and_types)
        ## the types of input variables: check if these types in our 
        var_to_type = {}
        type_collection = []
        for var, type in vars_and_types:
            if type.lower() not in ["tensor", "int", "bool", "str", "float", "scalar", "list"]:
                msg = type + " is not considered -> Considering only the following variable types: {Tensor, Int, Bool, Str, Float, Scalar, List}. Otherwise, return 'None'."
                msgs.append(msg)
                return 0, msg

            cnt = 1
            tmp = type.lower() + "_" + str(cnt)
            
            while tmp in type_collection:
                cnt += 1
                tmp = type.lower() + "_" + str(cnt)
                
            var_to_type[var.lower()] = tmp
            type_collection.append(tmp)

        print("------ var_to_type:", var_to_type)

        print("---- check Requirement")
        # check 2: check if the extracted requirements contain input variables in valid format
        check_requirement = check_info["Requirement"].lower()
        vars = re.findall(r'`([^`]+)`', check_requirement)
        if not vars:
            msg = '''The format of variables in the Requirement is not in the valid format -> Answer this question following "`<variable name>` should <requirement>", such as "the `input_t` shuold be a 2D tensor". Note that variable names should be enclosed in backticks(``).'''
            return 0, msg
        vars = list(set(vars))
        types = []
        for var in vars:
            if var not in var_to_type.keys():
                msg = "The variables used in 'Requirement' is not compatible with the 'The checked input variables' -> Please check the 'Requirement' and the 'The checked input variables'."
                return 0, msg
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
        




def reask(dialog, extract_res, MAX_TRY, all_mutators):
    SUCCESS = 0
    try_cnt = 0
    while try_cnt < MAX_TRY:
        print("* try_cnt:", try_cnt)
        # print(dialog)
        raw_llm = request_openai_api(dialog, 20)
        # print("raw_llm:", raw_llm)

        if try_cnt == MAX_TRY - 1:
            valid, res = extract_res_last_time(raw_llm) 
        else:
            valid, res = extract_res(raw_llm) 

        print("* res:", res)
        if valid:
            for pattern in res:
                all_mutators.append(pattern)
        # print("valid:", valid)

        if valid:
            SUCCESS = 1
            break
        else:
            dialog.append(
                {"role": "assistant", "content": raw_llm}
            )
            dialog.append(
                {"role": "user", "content": res + " \nPlease generate again."}
            )

        try_cnt += 1
    
    if SUCCESS:
        return res
    else:
        print("---- Can not finish this task. Here are the unsloved problem:", res)
        return None



if __name__ == "__main__":
    features = ["TORCH_CHECK"] # The CHECK FUNCTION NAME that you want to analyze
    target_directory = './pytorch/aten/src/ATen/native' # The source code path of Pytorch
    filename = "all_mutators.json"
    
    sketelon_database = []
    res = []
    check_id = [0]
    cpp_files = find_cpp_files(target_directory)
    for cpp_file in cpp_files:
        print("\n\n[[cpp_file]]:", cpp_file)
        check_codes = analyze_cpp_file_main(cpp_file, features, sketelon_database, check_id)
        if check_codes:
            res.extend(check_codes)

    print(len(res))

    print("\n\n===== sketelon_database start =====")
    for tmp in sketelon_database:
        print(tmp)
    print("sketelon_database num:", len(sketelon_database))
    print("===== sketelon_database end =====\n\n")

    print("\n\n===== codes start =====")
    for tmp in res:
        print(tmp)
    print("codes num:", len(res))
    print("===== codes end =====\n\n")

    print("\n\n===== Prompt Start =====\n\n")
    with open('template.txt', 'r') as file:
        prompt_template = file.read()
    prompts = []
    for target_code in res:
        target_code = "".join(target_code)
        prompt = prompt_template.replace("<TARGET_CODE>", target_code)
        prompt = prompt.replace("<CHECK_FEATURE>", "TORCH_CHECK")
        prompts.append(prompt)


    messages_template = [
        {"role": "system", "content": "You are a coding expert."},
        {"role": "user", "content": ""}
    ]

    print("\n\n===== prompts start =====")
    all_mutators = []
    for prompt in tqdm(prompts, desc="Processing", unit="item"):
        print("\n------- prompt start --------")
        print(prompt)
        print("------- prompt end --------\n")

        print("\n------- reponse start --------")
        messages = messages_gen(prompt, messages_template)
        reask(messages, extract_res, 3, all_mutators)
        
        print("------- reponse end --------\n")
    print("===== prompts end =====\n\n")

    print("repeated_item:", repeated_item)
    with open(filename, 'w') as f:
        json.dump(all_mutators, f, indent=4)
    
