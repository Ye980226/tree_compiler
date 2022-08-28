import numpy as np
from .tree_structure import TreeStructure
from csnake import CodeWriter,Function,Variable,Struct
from .csnake_ext import Union
import os 

BASEDIR=os.path.dirname(os.path.abspath(__file__))
np.set_printoptions(suppress=True)
QUANTIZE_TEMPLATE_PATH=os.path.join(BASEDIR,"c_quantize_function_template.txt")
PREDICT_TEMPLATE_PATH=os.path.join(BASEDIR,"c_predict_function_template.txt")
class TreeCTranslator:

    def __init__(self,tree_stucture:TreeStructure,tree_num,max_depth,feature_num):
        self.tree_structure=tree_stucture
        split_features,leaf_values,threshold_bins,threshold_unique,th_len_0,th_begin_0=self.tree_structure.get_all_param()
        self.split_features=split_features
        self.leaf_values=leaf_values
        self.threshold_bins=threshold_bins
        self.tree_num=tree_num
        self.max_depth=max_depth
        self.threshold_unique=threshold_unique
        self.th_len_0=th_len_0
        self.th_begin_0=th_begin_0
        self.index=0
        self.leaf_value_index=0
        self.feature_num=feature_num
        self.function_mapper={1:self.one_block,2:self.two_block,3:self.three_block,4:self.four_block,5:self.five_block,6:self.five_block,7:self.seven_block}
    
    def to_c_code(self,tree_filename="tu0_loop_version.c",header_filename="header.h",main_filename="main_0.c"):
        self._to_tree_code(tree_filename)
        self._to_header_code(header_filename)
        self._to_main_code(main_filename)
    def _to_header_code(self,filename=None):
        cwr=CodeWriter()
        cwr.add_line("#pragma once")

        cwr.include("<stdlib.h>")
        cwr.include("<string.h>")
        cwr.include("<math.h>")
        cwr.include("<stdint.h>")
        Entry=Union("Entry",typedef=False)
        qvalue=Variable("qvalue","uint8_t")
        fvalue=Variable("fvalue","double")
        missing=Variable("missing","uint8_t")
        Entry.add_variable(missing)
        Entry.add_variable(fvalue)
        Entry.add_variable(qvalue)
        cwr.add_struct(Entry)
        predict_0 = Function(
         "predict_0", "double", arguments=(("data","union Entry *"),)
        )
        
        predict_margin_unit0 = Function(
         "predict_margin_unit0", "float", arguments=(("data","union Entry *"),)
        )
        cwr.add_function_prototype(predict_0)
        cwr.add_function_prototype(predict_margin_unit0)
        if filename is None:
            cwr.write_to_file("header.h")
        else:
            cwr.write_to_file(filename)
    def _to_main_code(self,filename=None):
        cwr=CodeWriter()
        quantize_code=CodeWriter()
        predict_code=CodeWriter()
        th_len=Variable("th_len_0","static const int",value=self.th_len_0)
        th_begin=Variable("th_begin_0","static const int",value=self.th_begin_0)
        threshold=Variable("threshold_0","static const double",value=self.threshold_unique)
        cwr.add_variable_initialization(th_len)
        cwr.add_variable_initialization(th_begin)
        cwr.add_variable_initialization(threshold)
        cwr.include("<stdlib.h>")
        cwr.include("header.h")
        quantize=Function("quantize_0","static inline uint8_t",arguments=(("val","double"),("fid","uint8_t")))
        with open(QUANTIZE_TEMPLATE_PATH) as f:
            """
            ToDo:
            use Jinja Template
            """
            quantize_code.add_lines(f.read().replace("{{offset}}",str(self.th_begin_0[-1]+self.th_len_0[-1])).split("\n"))
        predict=Function("predict_0","double",arguments=(("data","union Entry*"),))
        with open(PREDICT_TEMPLATE_PATH) as f:
            """
            ToDo:
            use Jinja Template
            """
            predict_code.add_lines(f.read().replace("{{FEATURE_NUM}}",str(self.feature_num)).split("\n"))
        
        quantize.add_code(quantize_code)
        predict.add_code(predict_code)
        cwr.add_function_definition(quantize)
        cwr.add_function_definition(predict)
        if filename is not None:
            cwr.write_to_file(filename)
        else:
            cwr.write_to_file("main_0.c")    
    def _to_tree_code(self,filename=None):
        cwr = CodeWriter()
        func_code=CodeWriter()
        data=Variable("data","union Entry*")

        predict_margin_unit0=Function(
            "predict_margin_unit0", "float", arguments=(data,)
        )
        # threshold_value=Variable("threshold_value","int")
        threshold_bins = Variable(
            "threshold_bins",
            primitive="static const uint8_t",
            value=self.threshold_bins
        )
        leaf_values = Variable(
            "leaf_values",
            primitive="static const float",
            value=self.leaf_values
        )
        split_features = Variable(
            "split_features",
            primitive="static const uint8_t",
            value=self.split_features
        )
        cwr.include("header.h")
        cwr.add_variable_initialization(threshold_bins)
        cwr.add_variable_initialization(leaf_values)
        cwr.add_variable_initialization(split_features)
        # TREENUM=100
        func_code.add_line("const float *leaf_value;")
        func_code.add_line("const uint8_t *threshold_bin;")
        func_code.add_line("const uint8_t *split_feature;")
        func_code.add_line("float sum=0.0;")
        func_code.add_line(f"const uint8_t leaf_node_num = {2**self.max_depth};")
        func_code.add_line(f"const uint8_t non_leaf_node_num = {2**self.max_depth-1};")
        print(self.tree_num)
        func_code.add_line(f"for(int i=0 ;i < {self.tree_num}; i++)")
        print(self.tree_num)
        func_code.open_brace()
        func_code.add_line("leaf_value=&leaf_values[i*leaf_node_num];")###threshold_value
        func_code.add_line("threshold_bin=&threshold_bins[i*non_leaf_node_num];")###data_index_value
        func_code.add_line("split_feature=&split_features[i*non_leaf_node_num];")###leaf_value
        self.function_mapper[self.max_depth](func_code)
        func_code.close_brace()
        func_code.add_line("return sum;")
        predict_margin_unit0.add_code(func_code)
        cwr.add_function_definition(predict_margin_unit0)
        # print(cwr)
        if filename is None:
            cwr.write_to_file("tu0_loop_version.c")
        else:
            cwr.write_to_file(filename)
        
    def if_statement(self,func_code:CodeWriter):
       
        func_code.add_line("if(data[split_feature[%d]].qvalue <= threshold_bin[%d])"%(self.index,self.index))
        self.index+=1
    def else_statement(self,func_code:CodeWriter):
        func_code.add_line("else")
    def sum_statement(self,func_code:CodeWriter):
        func_code.add_line("sum += (float)leaf_value[%d];"%(self.leaf_value_index))
        self.leaf_value_index+=1
    def one_block(self,func_code:CodeWriter):
        self.if_statement(func_code)
        func_code.open_brace()
        self.sum_statement(func_code)
        func_code.close_brace()
        self.else_statement(func_code)
        func_code.open_brace()
        self.sum_statement(func_code)
        func_code.close_brace()

    def two_block(self,func_code:CodeWriter):
        self.if_statement(func_code)
        func_code.open_brace()
        self.one_block(func_code)
        func_code.close_brace()
        self.else_statement(func_code)
        func_code.open_brace()
        self.one_block(func_code)
        func_code.close_brace()
    def three_block(self,func_code:CodeWriter):
        self.if_statement(func_code)
        func_code.open_brace()
        self.two_block(func_code)
        func_code.close_brace()
        self.else_statement(func_code)
        func_code.open_brace()
        self.two_block(func_code)
        func_code.close_brace()

    def four_block(self,func_code:CodeWriter):
        self.if_statement(func_code)
        func_code.open_brace()
        self.three_block(func_code)
        func_code.close_brace()
        self.else_statement(func_code)
        func_code.open_brace()
        self.three_block(func_code)
        func_code.close_brace()

    def five_block(self,func_code:CodeWriter):
        self.if_statement(func_code)
        func_code.open_brace()
        self.four_block(func_code)
        func_code.close_brace()
        self.else_statement(func_code)
        func_code.open_brace()
        self.four_block(func_code)
        func_code.close_brace()

    def six_block(self,func_code:CodeWriter):
        self.if_statement(func_code)
        func_code.open_brace()
        self.five_block(func_code)
        func_code.close_brace()
        self.else_statement(func_code)
        func_code.open_brace()
        self.five_block(func_code)
        func_code.close_brace()
    
    def seven_block(self,func_code:CodeWriter):
        self.if_statement(func_code)
        func_code.open_brace()
        self.six_block(func_code)
        func_code.close_brace()
        self.else_statement(func_code)
        func_code.open_brace()
        self.six_block(func_code)
        func_code.close_brace()
    
