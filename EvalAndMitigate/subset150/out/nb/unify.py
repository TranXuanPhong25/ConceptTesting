import sys; sys.path[:0] = ['/repo', '/repo/run']

# ---- cell 0
# filtered out the following:
# 1. Possible that changed method is added to fixed code (so not in buggy code) or removed from buggy code (so not in fixed code) so they are not collected in the first place
# 2. We identify the method by project name + method signature + focal method invoked, they are only identical if all 3 are identical, we then take intersection of fixed and buggy bugs based on this identification.
# 3. We remove the bugs where the focal method is private or default, as it is not trivial for generating unit tests for them.

# ---- cell 1
import json
import javalang.tree as ast
import javalang.parse as parse

# ---- cell 2
fixed_source_file = 'data/prompts/fixed_source_data_draft.jsonl'

# ---- cell 3
buggy_source_file = 'data/prompts/buggy_source_data_draft.jsonl'

# ---- override after cell 3
# subset150: read the drafts of the sampled bugs, not data/prompts/{fixed,buggy}_source_data_draft.jsonl
import os
fixed_source_file = os.environ['S150_FIXED_DRAFT']
buggy_source_file = os.environ['S150_BUGGY_DRAFT']


# ---- cell 4
def is_method_public_or_protected(java_code):
    # Parse the Java code
    wrapped_java_code = 'class Test {\n' + java_code.replace('\r\n', '\n\n') + '\n}'
    tree = parse.parse(wrapped_java_code)
    # search for constructor
    for path, node in tree.filter(ast.ConstructorDeclaration):
        if node:
            if 'public' in node.modifiers or 'protected' in node.modifiers:
                return True
            return False

    # Search for the method
    for path, node in tree.filter(ast.MethodDeclaration):
        if node:
            if 'public' in node.modifiers or 'protected' in node.modifiers:
                return True
            return False
    raise ValueError(f"Method not found in the {java_code}")

# ---- cell 5
is_method_public_or_protected("""BasicBlock(BasicBlock parent, Node root) {
      this.parent = parent;

      // only named functions may be hoisted.
      this.isHoisted = NodeUtil.isHoistedFunctionDeclaration(root);

      this.isFunction = root.getType() == Token.FUNCTION;

      if (root.getParent() != null) {
        int pType = root.getParent().getType();
        this.isLoop = pType == Token.DO ||
            pType == Token.WHILE ||
            pType == Token.FOR;
      } else {
        this.isLoop = false;
      }
    }""")

# ---- cell 6
fixed_bugs = {}
with open(fixed_source_file, 'r') as f:
    for line in f:
        loaded_json = json.loads(line)
        if is_method_public_or_protected(loaded_json["source:source_method_code_format"]):
            bug_name = "_".join(loaded_json["extra:project_name"].split("_")[:2])
            fixed_bugs[bug_name+loaded_json["source:source_method_signature"]+str(int(loaded_json["focal_method_invoked"]))] = loaded_json
        else:
            print(f"skipped json with private or default focal method: {loaded_json['source:source_method_signature']}")

# ---- cell 7
len(fixed_bugs)

# ---- cell 8
buggy_bugs = {}
with open(buggy_source_file, 'r') as f:
    for line in f:
        loaded_json = json.loads(line)
        if is_method_public_or_protected(loaded_json["source:source_method_code_format"]):
            bug_name = "_".join(loaded_json["extra:project_name"].split("_")[:2])
            buggy_bugs[bug_name+loaded_json["source:source_method_signature"]+str(int(loaded_json["focal_method_invoked"]))] = loaded_json
        else:
            print(f"skipped json with private or default focal method: {loaded_json['source:source_method_signature']}")

# ---- cell 9
len(buggy_bugs)

# ---- cell 14
# get intersection of fixed and buggy bugs
fixed_bugs_keys = set(fixed_bugs.keys())
buggy_bugs_keys = set(buggy_bugs.keys())
intersection = fixed_bugs_keys.intersection(buggy_bugs_keys)
len(intersection)

# ---- cell 15
unified_fixed_bugs = []
for key in intersection:
    unified_fixed_bugs.append(fixed_bugs[key])

# ---- cell 16
len(unified_fixed_bugs)

# ---- cell 17
unified_buggy_bugs = []
for key in intersection:
    unified_buggy_bugs.append(buggy_bugs[key])

# ---- cell 18
len(unified_buggy_bugs)

# ---- cell 20
# sort by extra:project_name
unified_fixed_bugs = sorted(unified_fixed_bugs, key=lambda x: x["extra:project_name"])

# ---- cell 24
# sort by extra:project_name
unified_buggy_bugs = sorted(unified_buggy_bugs, key=lambda x: x["extra:project_name"])

# ---- cell 27
unified_buggy_invoked = [invoked for invoked in unified_buggy_bugs if invoked["focal_method_invoked"]]

# ---- override after cell 27
# subset150: cell 28's records, written to S150_OUT instead of data/prompts/buggy_source_data_unified_invoked.jsonl
with open(os.environ['S150_OUT'], 'w') as f:
    for bug in unified_buggy_invoked:
        f.write(json.dumps(bug) + '\n')
print(len(unified_buggy_invoked), 'unified invoked ->', os.environ['S150_OUT'])

