import lightgbm
import numpy as np
import pandas as pd
X = np.random.randn(1000000, 40)
y = np.random.randn(1000000)
train_dataset = lightgbm.Dataset(X, y)
params = {
    "learning_rate": 1e-3,
    "max_depth": 5,
    "num_leaves": 20,
    "min_data_in_leaf": 100,
    "min_sum_hessian_in_leaf": 1000,
    "metric": "rmse"
}
model = lightgbm.train(params, train_dataset, 100, [
                       train_dataset], verbose_eval=False)

model.save_model("model_0.txt")
from tree_compiler import TreeStructure,TreeCTranslator
tree=TreeStructure()
tree.init_from_file("model_0.txt")
tree.get_tree_dataframe(perfect=True)
# split_feature, leaf_value, threshold_bins,threshold_unique,th_len_0,th_begin_0=tree.get_all_param()
TREENUM=100
MAX_DEPTH=5
FEATURE_NUM=40
# translator=TreeCTranslator(tree,TREENUM,MAX_DEPTH,FEATURE_NUM)
# translator.to_c_code()
translator=TreeCTranslator(tree,TREENUM,MAX_DEPTH,FEATURE_NUM)
translator.to_c_code()
