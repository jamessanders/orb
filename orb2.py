import parser
import sys
import copy

symbols = {}
symbols["orb"] = {}
symbols["locals"] = []

def debug(x):
    #print " [DEBUG] %s"%x
    pass

def setSymbol(context):
    def setaux(name, value):
        print "Setting: %s to %s" % (name, value)
        context[name] = value
    return setaux

class OrbFunction:
    def __init__(self, name, fn):
        self.name = name
        self.fn   = fn
    def __call__(self, *args):
        debug("Calling %s" % self.name)
        return self.fn(*args)
    def __repr__(self):
        return "<OrbFunction '%s'>" % self.name

def pushToCallStack(x):
    debug("Pushing '%s' to callStack" % x)
    callStack.append(x)
    argStack.append([])

def define(context, expr):
    fname = expr.items[1].items[0].value
    params = [x.value for x in expr.items[1].items[1:]]
    body = expr.items[2:]
    parent = (len(symbols["locals"]) > 0) and symbols["locals"][-1] or None
    def orbFn(*args):
        local = {}
        if parent != None:
            local["_parent"] = parent
        local["set"] = wrap("set",setSymbol(local))
        local["def"] = lambda x: define(local, x)
        i = 0
        for a in params:
            local[a] = args[i]
            i += 1
        symbols["locals"].append(local)
        def postExec(*args):
            if len(argStack) == 0:
                argStack.append([])
            argStack[-1].append(args[0][0])
            symbols["locals"].pop()
        pushToCallStack(OrbFunction("post-run", postExec))
        for i in range(0,len(body)):
            pushToCallStack(body[(len(body)-1)-i])

    context[fname] = OrbFunction(fname, orbFn)
    return context[fname]

def printS(x):
    print x
    return x

def setGlobal():
    return setSymbol(symbols["orb"])

def ifStatement(condition, yes, default):
    if condition:
        yes
    else:
        default

def makeList(*args):
    return list(args)

def wrap(name, fn):
    def wrapped(*args):
        results = fn(*args)
        debug("RESULTS: %s" % results)
        if len(argStack) > 0:
            argStack[-1].append(results)
        else:
            argStack.append([results])
    return OrbFunction(name, wrapped)

def tail(ls):
    if len(ls) == 0:
        raise Error("'tail' on empty list")
    elif len(ls) == 1:
        return []
    else:
        return ls[1:]


symbols["native"] = {
    "<=": wrap("<=", lambda a,b: a <= b),
    "+": wrap("+",lambda a,b: a+b),
    "*": wrap("*",lambda a,b: a*b),
    "-": wrap("-",lambda a,b: a-b),
    "/": wrap("/",lambda a,b: a/b),
    ":": wrap(":",lambda x, xs: [x] + xs),
    "def": wrap("def",lambda x: define(symbols["orb"], x)),
    "print": wrap("print",printS),
    "set": wrap("set",setGlobal()),
    "len": wrap("len",len),
    "id": wrap("id",lambda x: x),
    "head": wrap("head",lambda l: l[0]),
    "tail": wrap("tail",tail),
    "list": wrap("list",makeList),
    "==": wrap("==",lambda a,b: a == b),
    "<": wrap("<",lambda a,b: a < b),
    ">": wrap(">",lambda a,b: a > b),
    "empty": [],
    "exit": wrap("exit",lambda n: sys.exit(n)),
    "str":wrap("str",lambda x: str(x))
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

def makeStub(fname):
    def orbExec(args):
        call = resolveSymbol(fname)
        return call(*args)
    return OrbFunction("wrapped %s"%fname, orbExec)

callStack = []
argStack = []

def shiftArgStack():
    debug("Shifting Args")
    args = argStack.pop()
    if len(argStack) > 0:
        argStack[-1] = argStack[-1] + args
    else:
        argStack.append(args)
    return args
    

def evaluateExpression2():
    while len(callStack) > 0 :
        debug("")
        debug("-" * 72)
        debug(" ")
        debug(" + CALLstack: %s" % callStack)
        debug(" ")
        debug(" + ARGStack: %s" % argStack)
        debug(" ")
        debug("-" * 72)
        debug("")
        #debug("SYMBOLS: %s"%symbols["locals"])
        #debug("")
        #debug("-" * 72)
        expr = callStack.pop()
        if isinstance(expr, parser.Atom):
            shiftArgStack()
            if (expr.type == int):
                argStack[-1].append(int(expr.value))
            elif (expr.type == str):
                argStack[-1].append(str(expr.value))
            elif (expr.type == parser.symbol):
                argStack[-1].append(resolveSymbol(expr.value))
        elif isinstance(expr, parser.SExpr):                                                
            fname = expr.items[0].value
            if fname == "def":
                 argStack[-1].append(resolveSymbol("def")(expr))
            elif fname == "if":
                shiftArgStack()
                def makeIfTest(one, two):
                    def ifTest(cond):
                        debug("Cond: %s" % cond)
                        shiftArgStack()
                        if (cond[0]):
                            pushToCallStack(one)
                        else:
                            pushToCallStack(two)
                    return ifTest
                pushToCallStack(makeIfTest(expr.items[2], expr.items[3]))
                pushToCallStack(expr.items[1])
            else:
                debug("Creating stub from %s" % expr)
                shiftArgStack()
                pushToCallStack(makeStub(fname))
                for item in expr.items[1:]:
                    pushToCallStack(item)
        elif callable(expr):
            args = argStack.pop()
            args.reverse()
            debug("Calling %s with args: %s" % (expr, args))
            #print symbols
            expr(args)
        else:
           raise(Error("Unhandled: %s" % expr))
            
    return argStack[-1][0]


for a in expr:
    debug("--LINE--")
    pushToCallStack(a)
    evaluateExpression2()
    debug("FINAL CALLSTACK: %s" % callStack)
    debug("FINAL ARGSTACK: %s" % argStack)
    callStack = []
    argStack = []
