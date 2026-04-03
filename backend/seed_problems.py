"""
Seed Problems
Returns 3 sample problems preloaded on first startup:
1. Two Sum (Python) — requires for loop, bans while loop
2. Reverse Array (C) — requires while loop, bans for loop
3. Fibonacci (C++) — requires recursion, bans for/while loops
"""


def get_seed_problems() -> list[dict]:
    return [
        {
            "title": "Two Sum",
            "description": """## Two Sum

Given an array of integers `nums` and an integer `target`, return the **indices** of the two numbers such that they add up to `target`.

You may assume that each input would have **exactly one solution**, and you may not use the same element twice.

### Example 1
```
Input: nums = [2, 7, 11, 15], target = 9
Output: [0, 1]
Explanation: Because nums[0] + nums[1] == 9, we return [0, 1].
```

### Example 2
```
Input: nums = [3, 2, 4], target = 6
Output: [1, 2]
```

### Example 3
```
Input: nums = [3, 3], target = 6
Output: [0, 1]
```

### Constraints
- 2 ≤ nums.length ≤ 10⁴
- -10⁹ ≤ nums[i] ≤ 10⁹
- Only one valid answer exists.

### Requirements
- You **must** use a `for` loop.
- You **must not** use a `while` loop.
""",
            "topic_tags": ["Arrays", "Hash Table"],
            "difficulty": "Easy",
            "required_constructs": ["for_loop"],
            "banned_constructs": ["while_loop"],
            "templates": [
                {
                    "language": "python",
                    "template_code": """import sys

def two_sum(nums, target):
    # Write your solution here using a for loop
    # Return the indices of the two numbers that add up to target
    pass

# DO NOT MODIFY BELOW THIS LINE
if __name__ == "__main__":
    line1 = input().strip()
    line2 = input().strip()
    nums = list(map(int, line1.split(",")))
    target = int(line2)
    result = two_sum(nums, target)
    if result:
        print(f"{result[0]},{result[1]}")
    else:
        print("None")
""",
                    "editable_ranges": [
                        {"startLine": 4, "endLine": 6}
                    ],
                },
                {
                    "language": "java",
                    "template_code": """import java.util.*;

public class Solution {
    public static int[] twoSum(int[] nums, int target) {
        // Write your solution here using a for loop
        // Return the indices of the two numbers that add up to target
        return new int[]{};
    }

    // DO NOT MODIFY BELOW THIS LINE
    public static void main(String[] args) {
        Scanner scanner = new Scanner(System.in);
        String[] numsStr = scanner.nextLine().trim().split(",");
        int target = Integer.parseInt(scanner.nextLine().trim());
        int[] nums = new int[numsStr.length];
        for (int i = 0; i < numsStr.length; i++) {
            nums[i] = Integer.parseInt(numsStr[i].trim());
        }
        int[] result = twoSum(nums, target);
        if (result.length == 2) {
            System.out.println(result[0] + "," + result[1]);
        } else {
            System.out.println("None");
        }
    }
}
""",
                    "editable_ranges": [
                        {"startLine": 5, "endLine": 7}
                    ],
                },
                {
                    "language": "javascript",
                    "template_code": """const readline = require('readline');

function twoSum(nums, target) {
    // Write your solution here using a for loop
    // Return the indices of the two numbers that add up to target
    return [];
}

// DO NOT MODIFY BELOW THIS LINE
const rl = readline.createInterface({ input: process.stdin });
const lines = [];
rl.on('line', (line) => lines.push(line.trim()));
rl.on('close', () => {
    const nums = lines[0].split(',').map(Number);
    const target = parseInt(lines[1]);
    const result = twoSum(nums, target);
    if (result && result.length === 2) {
        console.log(result[0] + ',' + result[1]);
    } else {
        console.log('None');
    }
});
""",
                    "editable_ranges": [
                        {"startLine": 4, "endLine": 6}
                    ],
                },
            ],
            "test_cases": [
                {
                    "input_data": "2,7,11,15\n9",
                    "expected_output": "0,1",
                    "is_sample": 1,
                },
                {
                    "input_data": "3,2,4\n6",
                    "expected_output": "1,2",
                    "is_sample": 1,
                },
                {
                    "input_data": "3,3\n6",
                    "expected_output": "0,1",
                    "is_sample": 1,
                },
                {
                    "input_data": "1,5,3,7\n8",
                    "expected_output": "1,2",
                    "is_sample": 0,
                },
                {
                    "input_data": "-1,0,1,2\n1",
                    "expected_output": "0,2",
                    "is_sample": 0,
                },
            ],
        },
        {
            "title": "Reverse Array In-Place",
            "description": """## Reverse Array In-Place

Given an array of integers, reverse the array **in-place** using a `while` loop.

Print the reversed array elements separated by spaces.

### Example 1
```
Input: 1 2 3 4 5
Output: 5 4 3 2 1
```

### Example 2
```
Input: 10 20 30
Output: 30 20 10
```

### Example 3
```
Input: 42
Output: 42
```

### Constraints
- 1 ≤ array length ≤ 10⁵
- -10⁹ ≤ element ≤ 10⁹

### Requirements
- You **must** use a `while` loop for the reversal.
- You **must not** use a `for` loop.
""",
            "topic_tags": ["Arrays", "Two Pointers"],
            "difficulty": "Easy",
            "required_constructs": ["while_loop"],
            "banned_constructs": ["for_loop"],
            "templates": [
                {
                    "language": "c",
                    "template_code": """#include <stdio.h>
#include <stdlib.h>
#include <string.h>

void reverse_array(int arr[], int size) {
    // Write your solution here using a while loop
    // Reverse the array in-place

}

// DO NOT MODIFY BELOW THIS LINE
int main() {
    char line[100000];
    if (!fgets(line, sizeof(line), stdin)) return 1;
    
    int arr[100000];
    int size = 0;
    char *token = strtok(line, " \\t\\n");
    while (token != NULL) {
        arr[size++] = atoi(token);
        token = strtok(NULL, " \\t\\n");
    }
    
    reverse_array(arr, size);
    
    for (int i = 0; i < size; i++) {
        if (i > 0) printf(" ");
        printf("%d", arr[i]);
    }
    printf("\\n");
    return 0;
}
""",
                    "editable_ranges": [
                        {"startLine": 6, "endLine": 9}
                    ],
                },
                {
                    "language": "python",
                    "template_code": """def reverse_array(arr):
    # Write your solution here using a while loop
    # Reverse the array in-place
    pass

# DO NOT MODIFY BELOW THIS LINE
if __name__ == "__main__":
    nums = list(map(int, input().split()))
    reverse_array(nums)
    print(" ".join(map(str, nums)))
""",
                    "editable_ranges": [
                        {"startLine": 2, "endLine": 4}
                    ],
                },
                {
                    "language": "cpp",
                    "template_code": """#include <iostream>
#include <sstream>
#include <vector>
using namespace std;

void reverseArray(vector<int>& arr) {
    // Write your solution here using a while loop
    // Reverse the array in-place

}

// DO NOT MODIFY BELOW THIS LINE
int main() {
    string line;
    getline(cin, line);
    istringstream iss(line);
    vector<int> arr;
    int num;
    while (iss >> num) {
        arr.push_back(num);
    }
    
    reverseArray(arr);
    
    for (int i = 0; i < arr.size(); i++) {
        if (i > 0) cout << " ";
        cout << arr[i];
    }
    cout << endl;
    return 0;
}
""",
                    "editable_ranges": [
                        {"startLine": 7, "endLine": 10}
                    ],
                },
            ],
            "test_cases": [
                {
                    "input_data": "1 2 3 4 5",
                    "expected_output": "5 4 3 2 1",
                    "is_sample": 1,
                },
                {
                    "input_data": "10 20 30",
                    "expected_output": "30 20 10",
                    "is_sample": 1,
                },
                {
                    "input_data": "42",
                    "expected_output": "42",
                    "is_sample": 1,
                },
                {
                    "input_data": "1 2",
                    "expected_output": "2 1",
                    "is_sample": 0,
                },
                {
                    "input_data": "-5 0 5 10 -10",
                    "expected_output": "-10 10 5 0 -5",
                    "is_sample": 0,
                },
            ],
        },
        {
            "title": "Fibonacci Number (Recursive)",
            "description": """## Fibonacci Number (Recursive)

The **Fibonacci sequence** is defined as:
- F(0) = 0
- F(1) = 1
- F(n) = F(n-1) + F(n-2) for n > 1

Given an integer `n`, compute F(n) using **recursion**.

### Example 1
```
Input: 5
Output: 5
Explanation: F(5) = F(4) + F(3) = 3 + 2 = 5
```

### Example 2
```
Input: 10
Output: 55
```

### Example 3
```
Input: 0
Output: 0
```

### Constraints
- 0 ≤ n ≤ 30

### Requirements
- You **must** use **recursion** (the function must call itself).
- You **must not** use a `for` loop.
- You **must not** use a `while` loop.
""",
            "topic_tags": ["Recursion", "Math"],
            "difficulty": "Easy",
            "required_constructs": ["recursion"],
            "banned_constructs": ["for_loop", "while_loop"],
            "templates": [
                {
                    "language": "cpp",
                    "template_code": """#include <iostream>
using namespace std;

int fibonacci(int n) {
    // Write your recursive solution here
    // Base cases: F(0) = 0, F(1) = 1
    // Recursive case: F(n) = F(n-1) + F(n-2)
    return 0;
}

// DO NOT MODIFY BELOW THIS LINE
int main() {
    int n;
    cin >> n;
    cout << fibonacci(n) << endl;
    return 0;
}
""",
                    "editable_ranges": [
                        {"startLine": 5, "endLine": 8}
                    ],
                },
                {
                    "language": "python",
                    "template_code": """def fibonacci(n):
    # Write your recursive solution here
    # Base cases: F(0) = 0, F(1) = 1
    # Recursive case: F(n) = F(n-1) + F(n-2)
    pass

# DO NOT MODIFY BELOW THIS LINE
if __name__ == "__main__":
    n = int(input())
    print(fibonacci(n))
""",
                    "editable_ranges": [
                        {"startLine": 2, "endLine": 5}
                    ],
                },
                {
                    "language": "java",
                    "template_code": """import java.util.Scanner;

public class Solution {
    public static int fibonacci(int n) {
        // Write your recursive solution here
        // Base cases: F(0) = 0, F(1) = 1
        // Recursive case: F(n) = F(n-1) + F(n-2)
        return 0;
    }

    // DO NOT MODIFY BELOW THIS LINE
    public static void main(String[] args) {
        Scanner scanner = new Scanner(System.in);
        int n = Integer.parseInt(scanner.nextLine().trim());
        System.out.println(fibonacci(n));
    }
}
""",
                    "editable_ranges": [
                        {"startLine": 5, "endLine": 8}
                    ],
                },
                {
                    "language": "c",
                    "template_code": """#include <stdio.h>

int fibonacci(int n) {
    // Write your recursive solution here
    // Base cases: F(0) = 0, F(1) = 1
    // Recursive case: F(n) = F(n-1) + F(n-2)
    return 0;
}

// DO NOT MODIFY BELOW THIS LINE
int main() {
    int n;
    scanf("%d", &n);
    printf("%d\\n", fibonacci(n));
    return 0;
}
""",
                    "editable_ranges": [
                        {"startLine": 4, "endLine": 7}
                    ],
                },
                {
                    "language": "javascript",
                    "template_code": """const readline = require('readline');

function fibonacci(n) {
    // Write your recursive solution here
    // Base cases: F(0) = 0, F(1) = 1
    // Recursive case: F(n) = F(n-1) + F(n-2)
    return 0;
}

// DO NOT MODIFY BELOW THIS LINE
const rl = readline.createInterface({ input: process.stdin });
rl.on('line', (line) => {
    const n = parseInt(line.trim());
    console.log(fibonacci(n));
    rl.close();
});
""",
                    "editable_ranges": [
                        {"startLine": 4, "endLine": 7}
                    ],
                },
            ],
            "test_cases": [
                {
                    "input_data": "5",
                    "expected_output": "5",
                    "is_sample": 1,
                },
                {
                    "input_data": "10",
                    "expected_output": "55",
                    "is_sample": 1,
                },
                {
                    "input_data": "0",
                    "expected_output": "0",
                    "is_sample": 1,
                },
                {
                    "input_data": "1",
                    "expected_output": "1",
                    "is_sample": 0,
                },
                {
                    "input_data": "20",
                    "expected_output": "6765",
                    "is_sample": 0,
                },
            ],
        },
    ]
