from owlready2 import default_world,onto_path, ObjectProperty, DataProperty, rdfs, Thing 
onto_path.append('./smile_ks_parse_query/ontology_cache/')
import re, os, tqdm
from smile_ks_parse_query.listener import ParseQuery, Query, Text, Trace, Ks, KSAR, Hypothesis, Text, Ks, KSAR

from py2graphdb.config import config as CONFIG
from py2graphdb.utils.db_utils import resolve_nm_for_dict, PropertyList, _resolve_nm
from py2graphdb.ontology.namespaces import ic, geo, cids, org, time, schema, sch, activity, landuse_50872, owl
from py2graphdb.ontology.operators import *

from smile_base.utils import init_db
from smile_ks_parse_query.utils import add_ks


if not os.path.exists(CONFIG.LOG_DIR):
    os.makedirs(CONFIG.LOG_DIR)

smile = default_world.get_ontology(CONFIG.NM)
