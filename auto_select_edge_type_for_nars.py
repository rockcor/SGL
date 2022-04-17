from typing import Dict, List
from functools import reduce

import torch

from dataset.dblp import Dblp
from models.hetero_SGAP_models import NARS_SIGN, NARS_SIGN_WeightSharedAcrossFeatures, NARS_SGC_WithLearnableWeights, Fast_NARS_SGC_WithLearnableWeights
from tasks.node_classification import HeteroNodeClassification
from auto_choose_gpu import GpuWithMaxFreeMem

# Hyperparameters
PROP_STEPS = 3
HIDDEN_DIM = 256
NUM_LAYERS = 2
NUM_EPOCHS = 100
LR = 0.01
WEIGHT_DECAY = 0.0
BATCH_SIZE = 10000

dataset = Dblp(root='.', path_of_zip='./dataset/DBLP_processed.zip')
predict_class = dataset.TYPE_OF_NODE_TO_PREDICT


def GenerateSubgraphsWithSameEdgeTypeNum(random_subgraph_num: int, subgraph_edge_type_num: int) -> Dict:
    return dataset.nars_preprocess(edge_types=dataset.EDGE_TYPES,
                                   predict_class=dataset.TYPE_OF_NODE_TO_PREDICT,
                                   random_subgraph_num=random_subgraph_num,
                                   subgraph_edge_type_num=subgraph_edge_type_num)


# Input format: [(random_subgraph_num, subgraph_edge_type_num), ...]
# Each element is a tuple of (random_subgraph_num, subgraph_edge_type_num)
def GenerateSubgraphDict(subgraph_num_edge_type_num: List) -> Dict:
    subgraph_list = [GenerateSubgraphsWithSameEdgeTypeNum(
        random_subgraph_num, subgraph_edge_type_num)
        for random_subgraph_num, subgraph_edge_type_num
        in subgraph_num_edge_type_num]

    return reduce(lambda x, y: {**x, **y}, subgraph_list)


def Dict2List(dict: Dict) -> List:
    return [(key, dict[key]) for key in dict]


# Input format: [(random_subgraph_num, subgraph_edge_type_num), ...]
# Each element is a tuple of (random_subgraph_num, subgraph_edge_type_num)
def GenerateSubgraphList(subgraph_num_edge_type_num: List) -> List:
    return Dict2List(GenerateSubgraphDict(subgraph_num_edge_type_num))


def OneTrialWithSubgraphList(subgraph_num_edge_type_num: List) -> float:
    subgraph_list = GenerateSubgraphList(subgraph_num_edge_type_num)

    model = Fast_NARS_SGC_WithLearnableWeights(prop_steps=PROP_STEPS,
                                               feat_dim=dataset.data.num_features[predict_class],
                                               num_classes=dataset.data.num_classes[predict_class],
                                               hidden_dim=HIDDEN_DIM, num_layers=NUM_LAYERS,
                                               random_subgraph_num=len(subgraph_list))

    device = torch.device(
        f"cuda:{GpuWithMaxFreeMem()}" if torch.cuda.is_available() else "cpu")
    test_acc = HeteroNodeClassification(dataset, predict_class, model,
                                        lr=LR, weight_decay=WEIGHT_DECAY,
                                        epochs=NUM_EPOCHS, device=device,
                                        train_batch_size=BATCH_SIZE,
                                        eval_batch_size=BATCH_SIZE,
                                        subgraph_list=subgraph_list).test_acc

    raw_weight = model.subgraph_weight
    weight_sum = raw_weight.sum()
    normalized_weight = raw_weight/weight_sum
    print(normalized_weight)

    return test_acc


OneTrialWithSubgraphList([(3, 2), (3, 3)])