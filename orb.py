import parser
import sys
import copy

symbols = {}
symbols["orb"] = {}
symbols["locals"] = []

def setSymbol(context):
    def aux(name, value):
        context[name] = value
    return aux

def define(context, expr):
    fname = expr.items[1].items[0].value
    params = [x.value for x in expr.items[1].items[1:]]
    body = expr.items[2:]
    parent = (len(symbols["locals"]) > 0) and symbols["locals"][-1] or None
    def orbFn(*args):
        local = {}
        if parent != None:
            local["_parent"] = parent
        local["set"] = setSymbol(local)
        local["def"] = lambda x: define(local, x)
        i = 0
        for a in params:
            local[a] = args[i]
            i += 1
        symbols["locals"].append(local)
        output = []
        for statment in body:
            output.append(evaluateExpression(statment))
        symbols["locals"].pop()
        return output[-1]
    context[fname] = orbFn
    return orbFn

def printS(x): print x

def setGlobal():
    return setSymbol(symbols["orb"])

def ifStatement(condition, yes, default):
    if condition:
        yes
    else:
        default

def makeList(*args):
    return list(args)

symbols["native"] = {
    "+": lambda a,b: a+b,
    "*": lambda a,b: a*b,
    "-": lambda a,b: a-b,
    "/": lambda a,b: a/b,
    ":": lambda x, xs: [x] + xs,
    "def": lambda x: define(symbols["orb"], x),
    "print": printS,
    "set": setGlobal(),
    "len": len,
    "if": ifStatement,
    "id": lambda x: x,
    "head": lambda l: l[0],
    "tail": lambda l: l[1:],
    "list": makeList,
    "==": lambda a,b: a == b,
    "<": lambda a,b: a < b,
    ">": lambda a,b: a > b,
    "empty": [],
    "exit": lambda n: sys.exit(n)
}



expr = parser.parse(open(sys.argv[1]).read())

def resolveLocal(symbol, context):
    if context.has_key(symbol):
        return (True, context[symbol])
    elif context.has_key("_parent"):
        return resolveLocal(symbol, context["_parent"])
    else:
        return (False, None)

def resolveSymbol(symbol):
    (found, local) = (len(symbols["locals"]) > 0) and resolveLocal(symbol, symbols["locals"][-1]) or (False, None)
    if found:
        #print " - %s is local" % symbol
        #print symbols["locals"][-1]
        return local
    elif symbols["orb"].has_key(symbol):
        #print " - %s is defined in orb source" % symbol
        return symbols["orb"][symbol]
    elif symbols["native"].has_key(symbol):
        #print " - %s is native" % symbol
        return symbols["native"][symbol]    
    else:
        #print " - %s is not defined" % symbol
        return symbol


def evaluateExpression(expr):
    #print symbols["locals"]
    if isinstance(expr, parser.Atom):
        if (expr.type == int): return int(expr.value)
        if (expr.type == str): return str(expr.value)
        if (expr.type == parser.symbol):
            return resolveSymbol(expr.value)
    elif isinstance(expr, parser.SExpr):
        first = expr.items[0].value
        if first == "def":
            return resolveSymbol("def")(expr)
        elif first == "if":
            if evaluateExpression(expr.items[1]):
                return evaluateExpression(expr.items[2])
            else:
                return evaluateExpression(expr.items[3])
        else:
            call = resolveSymbol(first)
            val = [evaluateExpression(x) for x in expr.items[1:]]
            #print " - Calling: %s (%s) with arguments %s" % (first, call, val)
            return call(*val)

for a in expr:
    evaluateExpression(a)
