# *******
# * Read input from STDIN
# * Use print to output your result to STDOUT.
# * Use sys.stderr.write() to display debugging information to STDERR
# * ***/
import sys

lines = []
for line in sys.stdin:
    lines.append(line.rstrip('\n'))


def make_binary(x):
    if x < 2:
        return [x]
    return make_binary(x // 2) + [x % 2]


def make_base_31(x):
    if x < 31:
        return [x]
    return make_base_31(x // 31) + [x % 31]


# assert make_binary(1) == [1]
# assert make_binary(10) == [1, 0, 1, 0]


def xor(X, Y):
    max_len = max(len(X), len(Y))
    min_len = min(len(X), len(Y))
    diff = max_len - min_len
    if len(X) >= len(Y):
        full_X = X
        full_Y = diff * [0] + Y
    else:
        full_X = diff * [0] + X
        full_Y = Y
    return [int(x != y) for x, y in zip(full_X, full_Y)]


# [0, 36, 52, 35, 35, 51, 37, 32]
# # assert xor([0], [0]) == [0]
# # assert xor([0, 1, 0], [1, 1]) == [0, 0, 1]
# x = [chr(47), chr(42), chr(36), chr(43), chr(48), chr(54), chr(40)]


def not_(X):
    return [1 - x for x in X]


def make_decimal(X):
    return sum([2 ** i * x for i, x in enumerate(X[::-1])])


# assert make_decimal([1, 0]) == 2
# assert make_decimal([1, 0, 1, 0]) == 10
# assert make_decimal([0]) == 0
# assert make_decimal([1]) == 1


def gen_random():
    import random

    letters = [chr(i) for i in range(33, 127)]
    return ''.join([random.choice(letters) for _ in range(16)])


# X = gen_random()
# Y = gen_random()
# assert xor(xor(Y, X), X) == Y


def hash_(word):
    sum_ = sum([ord(char) * 31 ** (len(word) - 1 - i) for i, char in enumerate(word)])
    return sum_ % 4294967296


# assert hash_('Coolh4cker0780578') == 1548960877
# assert hash_('BigBoss') == 1548960877
# assert hash_('a') == ord('a')
# assert hash_('ab') == ord('b') + 31 * ord('a')


def solve(password_):
    password = password_[::-1]
    # hashed = hash_(password)
    for i, (x, y) in enumerate(zip(password, password[1:])):
        if ord(y) - 1 >= 33 and ord(x) + 31 <= 126:
            new_password = password[:i] + chr(ord(x) + 31) + chr(ord(y) - 1) + password[i + 2 :]
            return new_password[::-1]
        elif ord(y) + 1 <= 126 and ord(x) - 31 >= 33:
            new_password = password[:i] + chr(ord(x) - 31) + chr(ord(y) + 1) + password[i + 2 :]
            return new_password[::-1]
    last_char = password[-1]
    if ord(last_char) >= 35:
        return (password[:-1] + chr(ord(last_char) - 2) + chr(31 * 2))[::-1]
    zero_ = [47, 42, 36, 43, 48, 54, 40][::-1]
    for i, chr_ in enumerate(password):
        if i < len(zero_):
            zero_[i] += ord(chr_)
        else:
            zero_.append(ord(chr_))
    return ''.join([chr(x) for x in zero_])[::-1]

    # return new_password[::-1]


# KE7Z67WKIW


# def gen_random():
#     import random

#     letters = [chr(i) for i in range(33, 127)]
#     return ''.join([random.choice(letters) for _ in range(30)])


# for _ in range(1000):
#     rdm = gen_random()
#     assert hash_(solve(rdm)) == hash_(rdm) and solve(rdm) != rdm


def solve_io(lines):
    # ints = list(map(int, lines[1].split()))
    # lr = [[int(x) for x in line.split()] for line in lines[2:]]
    return solve(lines[0])


# assert (
#     solve_io(['5 4', '11 22 33 44 55', '1 3', '0 1', '2 2', '2 4'])
#     == '0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 1 0 1 0 0 0 1 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 1 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0'
# )

# assert solve_io(['5 4', '0 0 0 0 0', '0 0', '1 1', '2 2', '3 3']) == ('4 ' + ' '.join(['0'] * 255))
# assert solve_io(['5 4', '0 1 0 1 0', '0 1', '1 2', '2 3', '3 4']) == ('0 4 ' + ' '.join(['0'] * 254))

print(solve_io(lines))
