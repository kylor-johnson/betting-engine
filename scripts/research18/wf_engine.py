import json, sys
from engine.models import script
out={}
for adj in (False, True):
    rows=script.build_features(adjust=adj, outlier=False)
    res=script.walk_forward(rows)
    out[str(adj)]={"summary":script.summary(res),"game":res["game"],"team":res["team"]}
    print(adj, json.dumps(out[str(adj)]["summary"], default=str)[:1500], flush=True)
json.dump(out, open(sys.argv[1],"w"), default=str)
