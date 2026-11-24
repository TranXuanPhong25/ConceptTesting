# This block only runs if you execute math_tools.py directly
from .references import HumanEvalPlusReferencePrograms
if __name__ == "__main__":
   provider = HumanEvalPlusReferencePrograms()
   task0 = provider.for_task({"task_id": "HumanEval/0"})
   ref_p = task0["source"]
   print(ref_p)
   
