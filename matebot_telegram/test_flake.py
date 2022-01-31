def main():
    def compare(a, b):
        print(a(), "or", b())

    def func(x):
        print(x)

    try:
        print("Some code that may raise errors")
    except RuntimeError as exc:
        compare(
            lambda: func(exc),
            lambda: func(exc)
        )
