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

def gen_ksar(input:Text, output:Hypothesis, trace:Trace):
    ks = Ks.search(props={smile.hasPyName:'ParseQuery', hasonly(smile.hasInputDataLevels):[input.klass], hasonly(smile.hasOutputDataLevels):[output.klass]}, how='first')[0]
    ks_ar = KSAR()
    ks_ar.keep_db_in_synch = False
    ks_ar.ks = ks.id
    ks_ar.trace = trace.id
    ks_ar.cycle = 0
    hypo = input
    ks_ar.input_hypotheses = hypo.id
    hypo.for_ks_ars = ks_ar.inst_id

    ks_ar.save()
    ks_ar.keep_db_in_synch = True
    return ks_ar


smile = default_world.get_ontology(CONFIG.NM)
with smile:
    init_db.init_db()
    add_ks.add_ks()
    init_db.load_owl('./smile_ks_parse_query/ontology_cache/cids.ttl')

    description = "St.Mary's Church provides hot meals &amp; addiction support to 90% of homeless youth."
    trace = Trace(keep_db_in_synch=True)

    query = Query.find_generate(content=description, trace_id=trace.id)
    query.save()
    ks_ar = gen_ksar(input=query, output=Text, trace=trace)
    ks_ar.ks_status=0
    ks_ar.save()

with smile:
    ks_ar = ParseQuery.process_ks_ars(loop=False)
    ks_ar.load()
    outs = [Hypothesis(inst_id=hypo_id).cast_to_graph_type() for hypo_id in ks_ar.hypotheses]
for out in outs:
    try:
        print(out.id[:20], out.klass, out.certainty, out.show())
    except:
        pass