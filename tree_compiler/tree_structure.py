import lightgbm
import pandas as pd
import numpy as np

np.set_printoptions(suppress=True)

def rank_mapper_function(some_model_dataframe: pd.Series):
    some_model_dataframe_drop_duplicates = some_model_dataframe.drop_duplicates(
    )
    some_model_dataframe_drop_duplicates: pd.DataFrame = pd.concat(
        (some_model_dataframe_drop_duplicates,
         some_model_dataframe_drop_duplicates.argsort().argsort()),
        axis=1)
    some_model_dataframe_drop_duplicates.columns = ["threshold", "rank"]
    mapper = some_model_dataframe_drop_duplicates.set_index(
        "threshold")["rank"].to_dict()
    return some_model_dataframe.map(mapper)


def insert(df: pd.DataFrame, i: int, df_add: pd.DataFrame):
    # 指定第i行插入一行数据
    df1 = df.iloc[:i, :]
    df2 = df.iloc[i + 1:, :]
    df_new = pd.concat([df1, df_add, df2], ignore_index=True)
    return df_new


class TreeStructure:
    def _init(self):
        self.tree_dataframe = self._get_tree_structure_dataframe()
        self.feature_num=self.model.num_feature()
    def init_from_file(self, filename: str):
        self.model = lightgbm.Booster(model_file=filename)
        self._init()

    def init_from_model(self, model: lightgbm.Booster):
        self.model = model
        self._init()

    def _get_tree_structure_dataframe(self):
        df: pd.DataFrame = self.model.trees_to_dataframe()
        is_leaf=(df["left_child"].isna())&(df["right_child"].isna())
        df["threshold_bins"] = df.groupby("split_feature")["threshold"].apply(
            rank_mapper_function)
        self.max_depth = df["node_depth"].max() - 1
        return df

    def _construct_perfect_binary_tree(self, tree_structure: pd.DataFrame):
        tree_structure = tree_structure.reset_index(drop=True)
        tree_structure["is_leaf"] = (tree_structure["left_child"].isna()) & (
            tree_structure["right_child"].isna())  ##只需要concat到不存在的位置就行了
        tree_structure["is_last_level"] = tree_structure[
            "node_depth"] == self.max_depth + 1
        tree_structure[
            "need_expand_level"] = self.max_depth + 1 - tree_structure[
                "node_depth"]
        unprocessed_tree_structure = tree_structure[
            (tree_structure["is_leaf"]) & (~tree_structure["is_last_level"])]
        while True:
            if unprocessed_tree_structure.shape[0] > 0:
                index = unprocessed_tree_structure.index[0]
                row = unprocessed_tree_structure.iloc[0]
                need_expand_level = row["need_expand_level"]
                current_node_depth = row["node_depth"]
                # print(index,need_expand_level,current_node_depth)
                df_add = pd.DataFrame(row.values.reshape(1, -1).repeat(
                    2**(need_expand_level + 1) - 1, axis=0),
                                      columns=row.index)
                df_add["node_depth"] = np.concatenate(
                    [[current_node_depth + j for _ in range(2**j)]
                     for j in range(need_expand_level + 1)])
                df_add.loc[df_add.index[:-2**need_expand_level],
                           ["left_child", "right_child"]] = "placeholder"
                df_add.loc[df_add.index[:], ["threshold_bins"]] = 255
                tree_structure = insert(tree_structure, index, df_add)
                tree_structure["is_leaf"] = (
                    tree_structure["left_child"].isna()) & (
                        tree_structure["right_child"].isna()
                    )  ##只需要concat到不存在的位置就行了
                tree_structure["is_last_level"] = tree_structure[
                    "node_depth"] == self.max_depth + 1
                tree_structure[
                    "need_expand_level"] = self.max_depth + 1 - tree_structure[
                        "node_depth"]
                unprocessed_tree_structure = tree_structure[
                    (tree_structure["is_leaf"])
                    & (~tree_structure["is_last_level"])]
                # print(unprocessed_tree_structure)
            else:
                break
        return tree_structure

    def get_tree_dataframe(self, perfect=True):
        if perfect:
            print(
                "default param 'perfect' need some time to construct a perfect binary tree"
            )
            self.tree_dataframe = self.tree_dataframe.groupby(
                "tree_index").apply(
                    self._construct_perfect_binary_tree).droplevel(
                        0, axis=0).reset_index(drop=True)
            self.tree_dataframe["split_feature"] = self.tree_dataframe[
                "split_feature"].fillna(method="ffill")
        return self.tree_dataframe

    def get_split_feature(self):
        return self.tree_dataframe[~self.tree_dataframe["is_leaf"]][
            "split_feature"].str[7:].values.astype(int)

    def get_leaf_value(self):
        return self.tree_dataframe[
            self.tree_dataframe["is_leaf"]]["value"].values

    def get_threshold_bins(self):
        return self.tree_dataframe[~self.tree_dataframe["is_leaf"]][
            "threshold_bins"].values.astype(int)

    def get_threshold_unique(self):
        threshold_unique=[]
        grouper=self.tree_dataframe.groupby("split_feature")
        columns=grouper.groups.keys()
        for i in range(self.feature_num):
            if f"Column_{i}" in columns:
                current_tree_dataframe=grouper.get_group(f"Column_{i}")
                threshold_unique.extend(current_tree_dataframe["threshold"].dropna().sort_values().unique())
        return np.asarray(threshold_unique)
    def get_threshold_leaf_map(self):

        first_tree_dataframe:pd.DataFrame=self.tree_dataframe[self.tree_dataframe["tree_index"]==0]
        print(first_tree_dataframe)
        sub_leaf_index=first_tree_dataframe[first_tree_dataframe["node_depth"]==self.max_depth-1].index.tolist()
        print(sub_leaf_index)
        array_len=[0]*(max(sub_leaf_index)+2)
        offset=0
        for s_i in sub_leaf_index:
            array_len[s_i]=offset
            array_len[s_i+1]=offset+1
            offset+=2
        return np.asarray(array_len)
    def get_th_len(self):
        th_len=[]
        grouper=self.tree_dataframe.groupby("split_feature")
        columns=grouper.groups.keys()
        for i in range(self.feature_num):
            if f"Column_{i}" in columns:
                current_tree_dataframe=grouper.get_group(f"Column_{i}")
                th_len.append(len(current_tree_dataframe["threshold"].dropna().unique()))
            else:
                th_len.append(0)
        return np.asarray(th_len)
    
    def get_th_begin(self):
        th_len=self.get_th_len()
        th_begin=[sum(th_len[:i]) for i in range(len(th_len))]
        return np.asarray(th_begin)

    def get_all_param(self):
        """
        return split_feature,leaf_value,threshold_bins
        """
        split_feature, leaf_value, threshold_bins,threshold_unique,th_len_0,th_begin_0 = self.get_split_feature(
        ), self.get_leaf_value(), self.get_threshold_bins(),self.get_threshold_unique(),self.get_th_len(),self.get_th_begin()
        print(">> split_feature shape is ", split_feature.shape)
        print(">> leaf_value shape is ", leaf_value.shape)
        print(">> threshold_bins shape is ", threshold_bins.shape)
        print(">> threshold_unique shape is ", threshold_unique.shape)
        print(">> th_len_0 shape is ", th_len_0.shape)
        print(">> th_begin_0 shape is ", th_begin_0.shape)
        return split_feature, leaf_value, threshold_bins,threshold_unique,th_len_0,th_begin_0
