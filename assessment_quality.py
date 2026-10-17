"""Bounded, exact numeric comparisons and conservative assessment checks."""
import ast
import re
import unicodedata
from fractions import Fraction


def numeric_value(text):
    text=str(text).strip().replace('−','-').replace('×','*').replace('÷','/')
    text=''.join(str(unicodedata.decimal(char)) if char.isdecimal() else char for char in text)
    if len(text)>160:return None
    text=re.sub(r'\\(?:d?frac)\{([^{}]+)\}\{([^{}]+)\}',r'((\1)/(\2))',text)
    text=text.replace('\\(','').replace('\\)','').strip('$ ')
    percent=text.endswith('%');text=text.rstrip('%').strip().replace('^','**')
    try:
        tree=ast.parse(text,mode='eval')
        if len(list(ast.walk(tree)))>40:return None
        def visit(node):
            if isinstance(node,ast.Expression):value=visit(node.body)
            elif isinstance(node,ast.Constant) and type(node.value) in (int,float):value=Fraction(ast.get_source_segment(text,node))
            elif isinstance(node,ast.UnaryOp) and isinstance(node.op,(ast.UAdd,ast.USub)):
                value=visit(node.operand)*(-1 if isinstance(node.op,ast.USub) else 1)
            elif isinstance(node,ast.BinOp):
                a,b=visit(node.left),visit(node.right)
                if isinstance(node.op,ast.Add):value=a+b
                elif isinstance(node.op,ast.Sub):value=a-b
                elif isinstance(node.op,ast.Mult):value=a*b
                elif isinstance(node.op,ast.Div):value=a/b
                elif isinstance(node.op,ast.Pow) and b.denominator==1 and abs(b)<=8:value=a**int(b)
                else:raise ValueError()
            else:raise ValueError()
            if max(abs(value.numerator),value.denominator)>10**100:raise ValueError()
            return value
        result=visit(tree)
        return result/100 if percent else result
    except (ValueError,SyntaxError,ZeroDivisionError,OverflowError,TypeError):return None


def equivalent(a,b):
    x,y=numeric_value(a),numeric_value(b)
    return (x is not None and y is not None and x==y) or ' '.join(a.casefold().split())==' '.join(b.casefold().split())


def vector_zero_case(question):
    """Exact zero-denominator cases only; never assume a zero dot product is an angle."""
    text=question.casefold().replace('−','-')
    vectors={}
    for name,body in re.findall(r'\b([ab])\s*=\s*\(([^()]{1,100})\)',text):
        values=[numeric_value(part) for part in body.split(',')]
        if len(values) in (2,3) and all(value is not None for value in values):vectors[name]=values
    zeros={name for name,values in vectors.items() if all(value==0 for value in values)}
    undefined=False
    if re.search(r'angle|કોણ|कोण',text) and len(vectors)==2 and zeros:undefined=True
    if re.search(r'unit vector|એકમ સદિશ|मात्रक सदिश',text):
        target=re.search(r'unit vector\s+(?:of|along|in the direction of)\s+(?:vector\s+)?([ab])\b',text)
        if len(vectors)>1 and not target:return None
        undefined=target[1] in zeros if target else bool(zeros or re.search(r'zero vector|null vector|શૂન્ય સદિશ|शून्य सदिश|\(\s*0\s*,\s*0\s*(?:,\s*0\s*)?\)',text))
    if 'projection' in text:
        target=re.search(r'(?:onto|on|along)\s+(?:the )?(?:vector )?([ab])\b',text)
        if target and target[1] in zeros:undefined=True
        elif target and len(vectors)==2 and zeros and target[1] not in zeros:
            return dict(undefined=False,value=Fraction(0),explanation='The projected vector is zero and the target vector is nonzero, so the projection is zero.')
    if undefined:return dict(undefined=True,explanation='Undefined: the formula divides by a zero vector magnitude. A zero dot product alone does not establish a right angle.')
    return None


def dice_probability(question):
    text=question.lower()
    if re.search(r'\b(?:sides|faces|numbered|tetrahedral|tetrahedron)\b',text):return None
    if len(text)>250 or re.search(r'\b(?:given|provided|and|or|conditional|product|odd|even|distinct|different|prime|only|biased|loaded|not)\b',text):return None
    match=re.search(r'\b(\d{1,2}|one|two|three|four|five|six|seven|eight|nine|ten) fair (?:six.sided )?(?:dice|die)\b',text)
    limit=re.search(r'\b(?:sum|total)\b[^\d?]{0,45}\b(at least|at most|exactly|greater than|less than)\s+(\d{1,3})\b',text)
    if not match or not limit or not re.search(r'\b(?:rolled|roll|thrown)\b',text):return None
    words=['one','two','three','four','five','six','seven','eight','nine','ten']
    n=words.index(match[1])+1 if match[1] in words else int(match[1])
    if not 1<=n<=10:return None
    bound=int(limit[2]);counts={0:1}
    for _ in range(n):
        next_counts={}
        for total,count in counts.items():
            for face in range(1,7):next_counts[total+face]=next_counts.get(total+face,0)+count
        counts=next_counts
    checks={'at least':lambda s:s>=bound,'at most':lambda s:s<=bound,'exactly':lambda s:s==bound,'greater than':lambda s:s>bound,'less than':lambda s:s<bound}
    favourable=sum(count for total,count in counts.items() if checks[limit[1]](total))
    total=6**n
    return Fraction(favourable,total),f'{favourable} favourable ordered outcomes out of {total} equally likely outcomes. Probability = {favourable}/{total} = {Fraction(favourable,total)}.'


def check(question):
    options=question['options'];key=question['correct_option'];explanation=question['explanation']
    accepted=[letter for letter,text in options.items() if equivalent(text,options[key])]
    vector=vector_zero_case(question['question'])
    if vector:
        if vector['undefined']:
            accepted=[letter for letter,text in options.items() if re.search(r'undefined|not defined|not possible|અવ્યાખ્યાયિત|વ્યાખ્યાયિત નથી|અનિર્ધારિત|अपरिभाषित|परिभाषित नहीं',text,re.I)]
        else:accepted=[letter for letter,text in options.items() if numeric_value(text)==vector['value']]
        return dict(accepted=accepted,verified=True,explanation=vector['explanation'],issue='' if accepted else 'No option matches the independently checked vector domain.')
    oracle=dice_probability(question['question'])
    if oracle:
        value,explanation=oracle
        accepted=[letter for letter,text in options.items() if numeric_value(text)==value]
        return dict(accepted=accepted,verified=True,explanation=explanation,issue='' if accepted else 'No option matches the independently calculated answer.')
    declared=re.findall(r'\b(?:option|વિકલ્પ|विकल्प)\s*([ABCD])\s*(?:is|છે|है)?\s*(?:the )?(?:correct|સાચો|सही)|\bcorrect (?:answer|option)\s*(?:is|:)\s*([ABCD])\b',explanation,re.I)
    letters={next(part.upper() for part in match if part) for match in declared}
    issue='The answer key and explanation disagree.' if letters-set(accepted) else ''
    if re.search(r'\bwait[.!…]|let[’\x27]?s re.verify|let me (?:re)?(?:check|verify)|\bcorrection:',explanation,re.I):issue='The explanation contains unfinished self-correction.'
    return dict(accepted=[] if issue else accepted,verified=False,explanation=explanation,issue=issue)


def validate(question):
    options=list(question['options'].values())
    if any(equivalent(a,b) for index,a in enumerate(options) for b in options[index+1:]):
        raise ValueError('Question validation failed: equivalent answer options. Nothing was saved; retry with a narrower topic.')
    result=check(question)
    if result['issue'] or (result['verified'] and question['correct_option'] not in result['accepted']):
        raise ValueError('Question validation failed: inconsistent answer key or explanation. Nothing was saved; retry.')
