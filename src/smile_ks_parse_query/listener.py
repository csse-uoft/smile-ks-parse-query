import re, os, pandas as pd
import pprint
from owlready2 import default_world, ObjectProperty, DataProperty, rdfs, Thing 
from py2graphdb.config import config as CONFIG
smile = default_world.get_ontology(CONFIG.NM)
with smile:
    from py2graphdb.Models.graph_node import GraphNode, SPARQLDict
    from py2graphdb.utils.db_utils import resolve_nm_for_dict, PropertyList
    from smile_ks_parse_query.utils import add_ks

    from smile_base.Model.knowledge_source.knowledge_source import KnowledgeSource    
    from smile_base.Model.data_level.hypothesis import Hypothesis
    from smile_base.Model.data_level.org_certainty     import OrgCertainty
    from smile_base.Model.data_level.query      import Query
    from smile_base.Model.data_level.text      import Text
    from smile_base.Model.controller.ks        import Ks
    from smile_base.Model.controller.ks_ar     import KSAR
    from smile_base.Model.controller.trace     import Trace


from nltk.tokenize import word_tokenize 

import numpy as np
import time

class ParseQuery(KnowledgeSource):
    """
    A knowledge source class that processes QA1 Ner

    Attributes
    ----------
    description: str
        String of description to be parsed
    annotation: Dict
        Formatted annotation for each task
    corenlp_output: Dict
        Annotated output of StanfordCoreNLP parser
    """
    current_trace = None
    current_ks_ar = None
    def __init__(self, hypothesis_ids, ks_ar, trace):
        fields = [v for v in Ks.ALL_KS_FORMATS.values() if v[0] == self.__class__.__name__][0]
        super().__init__(fields[1], fields[2], fields[3], trace, hypothesis_ids, ks_ar)

        self.query = None
        self.store_hypotheses = []

    @classmethod
    def process_ks_ars(cls, loop=True):
        """
        A class method that processes all the ks_ars with py_name='ParseQuery' and status=0.

        :param cls: The class itself (implicit parameter).
        :type cls: type
        :return: None
        """
        while True:
            
            ks = Ks.search(props={smile.hasPyName:'ParseQuery'}, how='first')
            if len(ks) >0:
                ks = ks[0]
            else:
                continue
            ks_ar = KSAR.search(props={smile.hasKS:ks.id, smile.hasKSARStatus:0}, how='first')
            if len(ks_ar) > 0:
                ks_ar = ks_ar[0]
                cls.logger(trace_id=ks_ar.trace, text=f"Processing ks_ar with id: {ks_ar.id}")
                # Get the trace from the ks_ar
                trace = Trace(inst_id=ks_ar.trace)
                cls.current_trace = trace
                cls.current_ks_ar = ks_ar
                # Get the hypothesis ids from the ks_ar
                hypo_ids = ks_ar.input_hypotheses
                if len(hypo_ids) != 1:
                    raise(Exception(f"Bad Input Hypothesis Count {len(hypo_ids)}"))

                hypo = Hypothesis(inst_id=hypo_ids[0])
                hypo.cast_to_graph_type()
                if not isinstance(hypo, smile.Query): #check if Phras
                    raise(Exception(f"Bad Input Hypothesis Type {type(hypo)}"))

                
                # Construct an instance of the ks_object
                ks_object = cls(hypothesis_ids=hypo_ids, ks_ar=ks_ar, trace=trace)
                
                # Call ks_object.set_input() with the necessary parameters
                ks_ar.ks_status = 1
                ks_object.set_input(query=hypo.content)
                
                ks_ar.ks_status = 2               
                hypotheses = ks_object.get_outputs()
                for hypo in hypotheses:
                    ks_ar.hypotheses = hypo.id 
                    trace.hypotheses = hypo.id


                # log output
                LOG_FILE_TEMPLATE = CONFIG.LOG_DIR+'smile_trace_log.txt'
                filename = LOG_FILE_TEMPLATE.replace('.txt', f"_{trace.id}.txt")
                ks_ar.summary(filename=filename, method_info=ks_object.method_info)

                ks_ar.ks_status = 3
                cls.current_trace = None
                cls.current_ks_ar = None
                if not loop:
                    return ks_ar
            time.sleep(1)        

    def clean_input(self, content):
        text = re.sub(r'([a-z])\.([A-Z])', r'\1. \2', content)
        # replace acronyms with ABC
        for match in re.findall(r'\b(?:[A-Z]\.+\s+){2,}',text):   # "A. B. C."
            text = re.sub(match, match.replace('. ','')+' ', text)
        for match in re.findall(r'\b(?:[A-Z]\.+){2,}',text):      # "A.B.C."
            text = re.sub(match, match.replace('.','')+' ', text)
        for match in re.findall(r'\b(?:[A-Z]\s+){2,}',text):      # "A B C"
            text = re.sub(match, match.replace(' ','')+' ', text)

        # make misc replacements
        text = text.strip().                \
                replace('as well as','and').\
                replace("&amp;", " and ").  \
                replace("–", ' ').          \
                replace('-',' ').           \
                replace('%',' percent ').   \
                replace('+',' plus ').      \
                replace("“","'").          \
                replace("”","'").          \
                replace("\"","'").          \
                replace("\n",". ").          \
                replace("\r",". ").          \
                strip()

        text = re.sub(r' +', ' ', text)
        text = re.sub(r'\.+', '.', text)
        text = re.sub(r' \.', '.', text)
        return text

    def cosine_score(self,text1, text2):
        # sw contains the list of stopwords 
        res1 =[];res2 =[] 
        list1 = word_tokenize(text1)  
        list2 = word_tokenize(text2) 

        set1 = set(list1)
        set2 = set(list2)

        rvector = set1.union(set2)  
        for w in rvector: 
            if w in set1: res1.append(1) # create a vector 
            else: res1.append(0) 
            if w in set2: res2.append(1) 
            else: res2.append(0) 
        c = 0
        
        # cosine formula  
        for i in range(len(rvector)): 
                c+= res1[i]*res2[i] 
        res = c / float((sum(res1)*sum(res2))**0.5) 

        # adjust cosine for lengths of each string
        text_ratio = len(text1)/len(text2) if np.argmax([len(text1),len(text2)])==1 else len(text2)/len(text1)
        adjusted_res = res/text_ratio if np.argmax([res,text_ratio])==1 else text_ratio/res

        return adjusted_res

    def set_input(self, query):
        self.query = query
        self.method_info = ''

    def get_outputs(self):
                
        content = self.clean_input(content=self.query)
        new_certainty = self.cosine_score(self.query, content)
        certainty_info = {f'certainty adjustment': f"cosine similarity between original and new query"}
        self.method_info += pprint.pformat(certainty_info) + "\n"

        text = Text.find_generate(content=content, trace_id=self.trace.id, certainty=new_certainty)

        text.from_ks_ars = self.ks_ar.id
        org_certainty = OrgCertainty.generate(hypothesis_id=text.id, ks_ar_id = self.ks_ar.id, trace_id=self.trace.id, certainty=new_certainty)
        self.ks_ar.org_certainties = org_certainty.id
        text.org_certainties = org_certainty.id


        self.store_hypotheses = [text]

        return self.store_hypotheses

if __name__ == '__main__':
    print('ParseQuery started')
    add_ks.add_ks(reload_db=False)
    print('ParseQuery ready')

    with smile:
        while True:
            try:
                ParseQuery.process_ks_ars(loop=True)
            except KeyboardInterrupt:
                print('interrupted!')
                break
            except Exception as e:
                print(f"{type(e)}: {e}")
                if ParseQuery.current_ks_ar is not None:
                    failed_ks_ar = ParseQuery.current_ks_ar
                    org_status = failed_ks_ar.ks_status
                    failed_ks_ar.ks_status = -1
                    failed_ks_ar.save()
                    error_message = f"Failed KSAF(ParseQuery, cycle={failed_ks_ar.cycle})): {failed_ks_ar} with ks_status={org_status}"
                    print(error_message)
                    if ParseQuery.current_trace is not None:
                        ParseQuery.logger(trace_id=ParseQuery.current_trace, text=error_message)
                pass

