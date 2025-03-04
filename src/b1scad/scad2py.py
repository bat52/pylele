#!/usr/bin/env python3

""" converts scad to python """

# scad_parser.py
from __future__ import annotations
import textwrap
from sly import Parser

import sys, os
sys.path.append(os.path.join(os.path.dirname(__file__), "../"))

from b13d.api.utils import gen_scad_foo, snake2camel, file_replace_extension
from b1scad.scad2ast import scad2ast, OpenSCADLexer

class OpenSCADParser(Parser):
    tokens = OpenSCADLexer.tokens
    debugfile = 'parser.out'

    def __init__(self):
        self.result = []
        
    @_("op")
    def expr(self, t):
        return t.op
    
    @_("shape_set")
    def expr(self, t):
        return t.shape_set
    
    @_("op")
    def shape_set(self, t):
        return t.op
    
    @_("op shape_set")
    def shape_set(self, t):
        return f'{t.op} + {t.shape_set}'

    # operators
    @_('TRANSLATE LPAREN named_vector RPAREN LBRACE shape_set RBRACE')
    def op(self, p):
        return f"{p.shape_set}.mv({p.named_vector})"

    @_('UNION LPAREN RPAREN LBRACE shape_set RBRACE')
    def op(self, p):
        return f"{p.shape_set}"

    @_('DIFFERENCE LPAREN RPAREN LBRACE shape SEMICOLON shape_set RBRACE')
    def op(self, p):
        return f"{p.shape} - ({p.shape_set})"

    @_('DIFFERENCE LPAREN RPAREN LBRACE op shape_set RBRACE')
    def op(self, p):
        return f"{p.op} - ({p.shape_set})"

    @_('HULL LPAREN RPAREN LBRACE shape_set RBRACE')
    def op(self, p):
        return f"({p.shape_set}).hull()"

    @_('ROTATE LPAREN named_vector RPAREN LBRACE shape_set RBRACE')
    def op(self, p):
        return f"{p.shape_set}.rotate([{p.named_vector}])"

    @_('SCALE LPAREN named_vector RPAREN LBRACE shape_set RBRACE')
    def op(self, p):
        return f"{p.shape_set}.scale({p.named_vector})"

    # shapes
    @_("shape_set shape SEMICOLON ")
    def shape_set(self, t):
        return f"{t.shape_set} + {t.shape}"

    @_("shape SEMICOLON ")
    def shape_set(self, t):
        return t.shape
            
    @_('CUBE LPAREN vector RPAREN')
    def shape(self, p):
        return f"self.api.box({p.vector}, center=False)"

    @_('CUBE LPAREN NUMBER RPAREN')
    def shape(self, p):
        return f"self.api.box({p.NUMBER},{p.NUMBER},{p.NUMBER}, center=False)"

    @_('SPHERE LPAREN args RPAREN')
    def shape(self, p):
        return f"self.api.sphere({p.args})"

    @_('CYLINDER LPAREN args RPAREN')
    def shape(self, p):
        splitargs = str(p.args).split(',')
        if len(splitargs)==3:
            return f"self.api.cone_z({p.args})"
        if len(splitargs)==2:
            # probably still needs fixing
            return f"self.api.cylinder_z({p.args})"

    @_('SFN EQU NUMBER')
    def args(self, p):
        return ""

    @_('IDENTIFIER EQU NUMBER')
    def args(self, p):
        return f"{p.IDENTIFIER} = {str(p.NUMBER)}"
    
    @_('args COMMA args')
    def args(self, p):
        if p.args0 == "":
            return f"{p.args1}"
        if p.args1 == "":
            return f"{p.args0}"
        return f"{p.args0}, {p.args1}"

    @_('NUMBER')
    def args(self, p):
        return str(p.NUMBER)
    
    @_('LSQUARE args RSQUARE')
    def vector(self, p):
        return f"{p.args}"

    @_('IDENTIFIER EQU vector')
    def named_vector(self, p):
        return f"{p.vector}"

    @_('vector')
    def named_vector(self, p):
        return f"{p.vector}"

# Modify parser to output Python file
def scad2py(infname: str, view_ast: bool = True):

    ast = scad2ast(infname, view=view_ast)
    parser = OpenSCADParser()
    
    # ast2python
    print('Parsing...')
    python_code = parser.parse(ast)
    print('Parsing End!')

    assert python_code != ""

    # output_file = infname.replace('.scad', '.py')
    output_file = file_replace_extension(infname, ".py")

    # make sure output file is erased if exists
    if os.path.exists(output_file):
        os.remove(output_file)

    with open(output_file, 'w') as f:
        f.write(python_code)

    print(f"Python code generated: {output_file}")

class CodeGenerator:
    def __init__(self, output_file: TextIO):
        self.output = output_file
        self.indent = 0
        
    def write_template(self, retshape="", model="model", body=""):
        template = f"""
        #!/usr/bin/env python3
        
        \"""
        {model} Solid
        \"""

        import os
        import sys
        sys.path.append(os.path.join(os.path.dirname(__file__), '../../'))

        from b13d.api.solid import Solid, test_loop, main_maker
        from b13d.api.core import Shape

        class {snake2camel(model)}(Solid):
            \""" Generate a {model} \"""
            def gen(self) -> Shape:
                {body}
                return {retshape}

        def main(args=None):
            \""" Generate a {model} \"""
            return main_maker(module_name=__name__,
                        class_name='{snake2camel(model)}',
                        args=args)

        def test_{model}(self,apis=None):
            \""" Test {model} \"""
            test_loop(module=__name__,apis=apis)

        def test_{model}_mock(self):
            \""" Test {model} Mock \"""
            test_{model}(self, apis=['mock'])

        if __name__ == '__main__':
            main()
        """
        self.output.write(textwrap.dedent(template))
    
    def generate(self, infname: str, view_ast: bool = True):

        ast = scad2ast(infname, view=view_ast)
        parser = OpenSCADParser()
        
        # ast2python
        print('Parsing...')
        python_code = parser.parse(ast)
        print('Parsing End!')

        assert python_code != ""

        return python_code
    
# Modify parser to output Python file
def scad2py(infname: str, execute_en: bool = True):
   
    # generate output file
    output_path = file_replace_extension(infname, ".py")
    
    # generate module name
    fname = os.path.basename(output_path)
    basefname,_ = os.path.splitext(fname)
    modelname = snake2camel(basefname)

    # make sure output file is erased if exists
    if os.path.exists(output_path):
        os.remove(output_path)

    with open(output_path, 'w', encoding='utf8') as f:
        generator = CodeGenerator(f)
        
        # Generate main python code
        pyshape = generator.generate(infname)

        # generate python file code 
        generator.write_template(retshape=pyshape, model=modelname)
        print(f"Generated Python code saved to {output_path}")
    
    if execute_en:
        cmdstr = f'python3 {output_path} -odoff'
        print(cmdstr)
        os.system(cmdstr)

    return output_path, modelname

def b1scad():
    if len(sys.argv)<2:
        infname = "model.scad"
        print(f'Unspecified input file, generate default {infname}')
        gen_scad_foo(infname, module_en=False)
    else:
        infname = sys.argv[1]
    
    scad2py(infname)

if __name__ == "__main__":
    b1scad()