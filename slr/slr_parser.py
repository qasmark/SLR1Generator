from grammar import *
import argparse

eps = 'e'


def first_follow(g):
    def union(set_1, set_2):
        set_1_len = len(set_1)
        set_1 |= set_2

        return set_1_len != len(set_1)

    first = {symbol: set() for symbol in g.symbols}
    first.update((terminal, {terminal}) for terminal in g.terminals)
    follow = {symbol: set() for symbol in g.non_terminals}
    follow[g.start].add('$')

    while True:
        updated = False

        for head, bodies in g.grammar.items():
            for body in bodies:
                for symbol in body:
                    if symbol != eps:
                        updated |= union(first[head], first[symbol] - set(eps))

                        if eps not in first[symbol]:
                            break
                    else:
                        updated |= union(first[head], set(eps))
                else:
                    updated |= union(first[head], set(eps))

                aux = follow[head]
                for symbol in reversed(body):
                    if symbol == eps:
                        continue
                    if symbol in follow:
                        updated |= union(follow[symbol], aux - set(eps))
                    if eps in first[symbol]:
                        aux = aux | first[symbol]
                    else:
                        aux = first[symbol]

        if not updated:
            return first, follow


class SLRParser:
    def __init__(self, g):
        self.G_prime = Grammar(f"{g.start}' -> {g.start}\n{g.grammar_str}")
        self.max_G_prime_len = len(max(self.G_prime.grammar, key=len))
        self.G_indexed = []

        for head, bodies in self.G_prime.grammar.items():
            for body in bodies:
                self.G_indexed.append([head, body])

        self.first, self.follow = first_follow(self.G_prime)
        self.C = self.items(self.G_prime)
        self.action = list(self.G_prime.terminals) + ['$']
        self.goto_lst = list(self.G_prime.non_terminals - {self.G_prime.start})
        self.parse_table_symbols = self.action + self.goto_lst
        self.parse_table = self.construct_table()

    def closure(self, i):
        j = i

        while True:
            item_len = len(j)

            for head, bodies in j.copy().items():
                for body in bodies.copy():
                    if '.' in body[:-1]:
                        symbol_after_dot = body[body.index('.') + 1]

                        if symbol_after_dot in self.G_prime.non_terminals:
                            for G_body in self.G_prime.grammar[symbol_after_dot]:
                                j.setdefault(symbol_after_dot, set()).add(
                                    ('.',) if G_body == (eps,) else ('.',) + G_body)

            if item_len == len(j):
                return j

    def goto(self, i, x):
        goto_lst = {}

        for head, bodies in i.items():
            for body in bodies:
                if '.' in body[:-1]:
                    dot_pos = body.index('.')

                    if body[dot_pos + 1] == x:
                        replaced_dot_body = body[:dot_pos] + (x, '.') + body[dot_pos + 2:]

                        for C_head, C_bodies in self.closure({head: {replaced_dot_body}}).items():
                            goto_lst.setdefault(C_head, set()).update(C_bodies)

        return goto_lst

    def items(self, g_prime):
        collection = [self.closure({g_prime.start: {('.', g_prime.start[:-1])}})]

        while True:
            item_len = len(collection)

            for i in collection.copy():
                for x in g_prime.symbols:
                    goto_lst = self.goto(i, x)

                    if goto_lst and goto_lst not in collection:
                        collection.append(goto_lst)

            if item_len == len(collection):
                return collection

    def construct_table(self):
        parse_table = {r: {c: '' for c in self.parse_table_symbols} for r in range(len(self.C))}

        for i, I in enumerate(self.C):
            for head, bodies in I.items():
                for body in bodies:
                    if '.' in body[:-1]:  # CASE 2 a
                        symbol_after_dot = body[body.index('.') + 1]

                        if symbol_after_dot in self.G_prime.terminals:
                            s = f's{self.C.index(self.goto(I, symbol_after_dot))}'

                            if s not in parse_table[i][symbol_after_dot]:
                                if 'r' in parse_table[i][symbol_after_dot]:
                                    parse_table[i][symbol_after_dot] += '/'

                                parse_table[i][symbol_after_dot] += s

                    elif body[-1] == '.' and head != self.G_prime.start:  # CASE 2 b
                        for j, (G_head, G_body) in enumerate(self.G_indexed):
                            if G_head == head and (G_body == body[:-1] or G_body == (eps,) and body == ('.',)):
                                for f in self.follow[head]:
                                    if parse_table[i][f]:
                                        parse_table[i][f] += '/'

                                    parse_table[i][f] += f'r{j}'

                                break

                    else:  # CASE 2 c
                        parse_table[i]['$'] = 'acc'

            for A in self.G_prime.non_terminals:  # CASE 3
                j = self.goto(I, A)

                if j in self.C:
                    parse_table[i][A] = self.C.index(j)

        return parse_table

    def print_info(self):
        def fprint(text, variable):
            print(f'{text:>12}: {", ".join(variable)}')

        def print_line():
            print(f'+{("-" * width + "+") * (len(list(self.G_prime.symbols) + ["$"]))}')

        def symbols_width(symbols):
            return (width + 1) * len(symbols) - 1

        print('AUGMENTED GRAMMAR:')

        for i, (head, body) in enumerate(self.G_indexed):
            print(f'{i:>{len(str(len(self.G_indexed) - 1))}}: {head:>{self.max_G_prime_len}} -> {" ".join(body)}')

        print()
        fprint('TERMINALS', self.G_prime.terminals)
        fprint('NON_TERMINALS', self.G_prime.non_terminals)
        fprint('SYMBOLS', self.G_prime.symbols)

        print('\nFIRST:')
        for head in self.G_prime.grammar:
            print(f'{head:>{self.max_G_prime_len}} = {{ {", ".join(self.first[head])} }}')

        print('\nFOLLOW:')
        for head in self.G_prime.grammar:
            print(f'{head:>{self.max_G_prime_len}} = {{ {", ".join(self.follow[head])} }}')

        width = max(len(c) for c in {'ACTION'} | self.G_prime.symbols) + 2
        for r in range(len(self.C)):
            max_len = max(len(str(c)) for c in self.parse_table[r].values())

            if width < max_len + 2:
                width = max_len + 2

        print('\nPARSING TABLE:')
        print(f'+{"-" * width}+{"-" * symbols_width(self.action)}+{"-" * symbols_width(self.goto_lst)}+')
        print(f'|{"":{width}}|{"ACTION":^{symbols_width(self.action)}}|{"GOTO":^{symbols_width(self.goto_lst)}}|')
        print(f'|{"STATE":^{width}}+{("-" * width + "+") * len(self.parse_table_symbols)}')
        print(f'|{"":^{width}}|', end=' ')

        for symbol in self.parse_table_symbols:
            print(f'{symbol:^{width - 1}}|', end=' ')

        print()
        print_line()

        for r in range(len(self.C)):
            print(f'|{r:^{width}}|', end=' ')

            for c in self.parse_table_symbols:
                print(f'{self.parse_table[r][c]:^{width - 1}}|', end=' ')

            print()

        print_line()
        print()

    def lr_parser(self, w):
        buffer = f'{w} $'.split()
        pointer = 0
        a = buffer[pointer]
        stack = ['0']
        symbols = ['']
        results = {
            'step': [''],
            'stack': ['STACK'] + stack,
            'symbols': ['SYMBOLS'] + symbols,
            'input': ['INPUT'],
            'action': ['ACTION']
        }

        step = 0
        while True:
            s = int(stack[-1])
            step += 1
            results['step'].append(f'({step})')
            results['input'].append(' '.join(buffer[pointer:]))

            if a not in self.parse_table[s]:
                results['action'].append(f'ERROR: unrecognized symbol {a}')

                break

            elif not self.parse_table[s][a]:
                results['action'].append('ERROR: input cannot be parsed by given this file')

                break

            elif '/' in self.parse_table[s][a]:
                action = 'reduce' if self.parse_table[s][a].count('r') > 1 else 'shift'
                results['action'].append(f'ERROR: {action}-reduce conflict at state {s}, symbol {a}')

                break

            elif self.parse_table[s][a].startswith('s'):
                results['action'].append('shift')
                stack.append(self.parse_table[s][a][1:])
                symbols.append(a)
                results['stack'].append(' '.join(stack))
                results['symbols'].append(' '.join(symbols))
                pointer += 1
                a = buffer[pointer]

            elif self.parse_table[s][a].startswith('r'):
                head, body = self.G_indexed[int(self.parse_table[s][a][1:])]
                results['action'].append(f'reduce by {head} -> {" ".join(body)}')

                if body != (eps,):
                    stack = stack[:-len(body)]
                    symbols = symbols[:-len(body)]

                stack.append(str(self.parse_table[int(stack[-1])][head]))
                symbols.append(head)
                results['stack'].append(' '.join(stack))
                results['symbols'].append(' '.join(symbols))

            elif self.parse_table[s][a] == 'acc':
                results['action'].append('accept')

                break

        return results

    @staticmethod
    def print_lr_parser(results):
        def print_line():
            print(f'{"".join(["+" + ("-" * (max_len + 2)) for max_len in max_lens.values()])}+')

        max_lens = {key: max(len(value) for value in results[key]) for key in results}
        printing_sings = {
            'step': '>',
            'stack': '',
            'symbols': '',
            'input': '>',
            'action': ''
        }

        print_line()
        print(''.join(
            [f'| {history[0]:^{max_len}} ' for history, max_len in zip(results.values(), max_lens.values())]) + '|')
        print_line()
        for i, step in enumerate(results['step'][:-1], 1):
            print(''.join([f'| {history[i]:{just}{max_len}} ' for history, just, max_len in
                           zip(results.values(), printing_sings.values(), max_lens.values())]) + '|')

        print_line()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('grammar_file', type=argparse.FileType('r'), help='text file to be used as file.txt')
    parser.add_argument('-g', action='store_true', help='generate automaton')
    parser.add_argument('tokens', help='tokens to be parsed - all tokens are separated with spaces')
    args = parser.parse_args()

    g = Grammar(args.grammar_file.read())
    slr_parser = SLRParser(g)
    slr_parser.print_info()
    results = slr_parser.lr_parser(args.tokens)
    slr_parser.print_lr_parser(results)


if __name__ == '__main__':
    main()
