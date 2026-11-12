"""Lexical prototype. Pair-match score is NOT semantic off-topic probability."""
from dataclasses import dataclass
import re
import numpy as np

def features(vectorizer,questions,answers):
    q=vectorizer.transform(questions);a=vectorizer.transform(answers)
    cosine=np.asarray(q.multiply(a).sum(axis=1)).ravel()
    coverage=[]
    for qt,at in zip(questions,answers):
        words=set(re.findall(r'[가-힣A-Za-z]{2,}',qt));coverage.append(sum(w in at for w in words)/max(len(words),1))
    return np.column_stack([cosine,coverage])

@dataclass
class AlertPolicy:
    consecutive_required:int=2
    cooldown_s:float=15
    low:float=.2
    high:float=.8
    min_words:int=5
    streak:int=0
    last_alert_s:float=-1e9
    def update(self,text,score,audio_end_s,is_final=True):
        if not is_final:return {'state':'unstable_partial','would_alert':False,'streak':self.streak}
        if len(text.split())<self.min_words:
            self.streak=0;return {'state':'insufficient_evidence','would_alert':False,'streak':0}
        state='off_topic_candidate' if score<=self.low else 'on_topic_candidate' if score>=self.high else 'uncertain'
        self.streak=self.streak+1 if state=='off_topic_candidate' else 0
        alert=self.streak>=self.consecutive_required and audio_end_s-self.last_alert_s>=self.cooldown_s
        if alert:self.last_alert_s=audio_end_s;self.streak=0
        return {'state':state,'would_alert':alert,'streak':self.streak}
