"""Test integrity of dags."""
import glob
import importlib
import os
from typing import List

import pytest
from airflow.models import DAG
from airflow.utils.dag_cycle_tester import check_cycle

DAG_PATHS = glob.glob(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'dags', '*.py')))


@pytest.mark.parametrize('dag_path', DAG_PATHS)
def test_dag_integrity(dag_path: str):
    """Import dag files and check for DAG."""
    module_name = os.path.basename(dag_path)
    mod_spec = importlib.util.spec_from_file_location(module_name, dag_path)
    module = importlib.util.module_from_spec(mod_spec)
    mod_spec.loader.exec_module(module)
    module_objects = vars(module).values()
    dag_objects: List[DAG] = [var for var in module_objects if isinstance(var, DAG)]
    assert dag_objects

    for dag in dag_objects:
        check_cycle(dag)
