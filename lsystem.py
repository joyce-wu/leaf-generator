'''

Sources:
https://github.com/abiusx/L3D (to quickly test generated strings)
The Algorithmic Beauty of Plants, ch 1-2


Number of iterations
Default rotation
Default Branch thickness
Axiom
Rules
'''


class LNode:
	def __init__(self, l, *params):
		self.l = l
		self.params = params

	def __repr__(self):
		if not self.params:
			return self.l
		else:
			return self.l + '(' + ','.join('{:.3f}'.format(x) for x in self.params) + ')'


	def apply_rule(self, successors):
		ans = []
		for node_or_func in successors:
			if callable(node_or_func):
				ans.append(node_or_func(self))
			else:
				ans.append(node_or_func)
		return ans


def parse_lstring(s):
	i = 0
	ans = []
	while i < len(s):
		ch = s[i]
		if i+1 < len(s) and s[i+1] == '(':
			j = s.find(')', i+1)
			params = s[i+2:j]
			params = [float(x) for x in params.split(',')]
			ans.append(LNode(ch, *params))
			i = j + 1
		else:
			ans.append(LNode(ch))
			i += 1

	return ans


def lstring_to_str(lstring):
	return ''.join(str(lnode) for lnode in lstring)

def apply_rules(lstring, rules, n_iter):
	rule = parse_lstring("F[&FA]/(94.74)[&FA]/(132.62)[&FA]")
	
	ans = lstring
	
	for i in range(n_iter):
		ans = []
		for node in lstring:
			if node.l in rules.keys():
				ans += node.apply_rule(rules[node.l])
			else:
				ans.append(node)
		lstring = ans

	return ans


if __name__ == '__main__':
	axiom = parse_lstring("F(1)")
	print(axiom)
	rules = {
		# "F" : parse_lstring("F[&FA]/(94.74)[&FA]/(132.62)[&FA]")
		"F" : [LNode("F", 1), lambda ln: LNode("F", ln.params[0] + 1), LNode("F", 1)]
	}
	print(lstring_to_str(apply_rules(axiom, rules, 2)))









	