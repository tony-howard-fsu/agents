I wrote a Python program in the sandbox to calculate the first 1,000,000 terms of the Leibniz series for π:

```python
def leibniz_pi(terms: int = 1_000_000) -> float:
    total = 0.0
    sign = 1.0
    for k in range(terms):
        total += sign / (2 * k + 1)
        sign *= -1.0
    return 4 * total


if __name__ == "__main__":
    pi_approx = leibniz_pi()
    print(pi_approx)
```

I ran it successfully, and the output was:

```text
3.1415916535897743
```