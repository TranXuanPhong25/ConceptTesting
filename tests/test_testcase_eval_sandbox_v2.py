"""Regression tests for testcase_eval/sandbox_v2.py: the vendored upstream
TestCase-Eval sandbox, patched in place (see that module's docstring) rather
than reimplemented from scratch. Requires g++, javac/java, and python3 on
PATH, same as sandbox.py's own tests.
"""

import unittest

from testcase_eval.sandbox_v2 import MultiLanguageExecutor


class SandboxV2Tests(unittest.TestCase):
    def setUp(self):
        self.ex = MultiLanguageExecutor()

    def test_cpp_with_cassert_via_bits_stdcpp_header(self):
        code = """
#include <bits/stdc++.h>
using namespace std;
int main(){ assert(1==1); int a,b; cin>>a>>b; cout<<a+b<<endl; return 0; }
"""
        result = self.ex.execute("C++17 (GCC 7-32)", code, "3 4\n")
        self.assertEqual(result["result"], "success_run")
        self.assertEqual(result["output"], "7\n")

    def test_python_basic(self):
        code = "a=input().split()\nprint(int(a[0])+int(a[1]))\n"
        result = self.ex.execute("Python 3", code, "5 6\n")
        self.assertEqual(result["result"], "success_run")
        self.assertEqual(result["output"], "11\n")

    def test_java_main_in_non_public_class_alone(self):
        code = """
class Helper {
    public static void main(String[] args) {
        System.out.println("hello-nonpublic-main-simple");
    }
}
"""
        result = self.ex.execute("Java 21", code, "")
        self.assertEqual(result["result"], "success_run")
        self.assertEqual(result["output"], "hello-nonpublic-main-simple\n")

    def test_java_main_in_non_public_class_with_competing_public_class(self):
        """The case the original `_replace_java_class_name` (and a naive
        regex-only patch of it) both fail: a real public class other than
        the one holding `main` forces a filename mismatch after renaming."""
        code = """
class Helper {
    public static void main(String[] args) {
        System.out.println("hello-nonpublic-main");
    }
}
public class Other {
    int x;
}
"""
        result = self.ex.execute("Java 21", code, "")
        self.assertEqual(result["result"], "success_run")
        self.assertEqual(result["output"], "hello-nonpublic-main\n")

    def test_java_normal_public_main_class(self):
        code = """
import java.util.Scanner;
public class Main {
    public static void main(String[] args) {
        Scanner sc = new Scanner(System.in);
        int a = sc.nextInt(), b = sc.nextInt();
        System.out.println(a + b);
    }
}
"""
        result = self.ex.execute("Java 21", code, "7 8\n")
        self.assertEqual(result["result"], "success_run")
        self.assertEqual(result["output"], "15\n")

    def test_memory_limit_enforced_via_prlimit(self):
        code = """
#include <bits/stdc++.h>
using namespace std;
int main(){
    vector<char> v;
    while(true) v.resize(v.size()+1024*1024, 0);
    return 0;
}
"""
        result = self.ex.execute("C++17 (GCC 7-32)", code, "", memory_limit=64)
        self.assertEqual(result["result"], "memory_limit_exceeded")


if __name__ == "__main__":
    unittest.main()
