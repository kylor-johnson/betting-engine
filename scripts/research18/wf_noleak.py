import json, sys
from engine.models import script
rows=script.build_features(adjust=True, outlier=False)
base=script.BASE_FEATURES
variants={"no_qb_no_weather":tuple(f for f in base if f not in ("backup_qb","wind6","rain")),
          "no_weather":tuple(f for f in base if f not in ("wind6","rain")),
          "no_qb":tuple(f for f in base if f!="backup_qb")}
out={}
for k,f in variants.items():
    res=script.walk_forward(rows, features=f)
    out[k]={"game":res["game"],"summary":script.summary(res)}
    s=out[k]["summary"]
    print(k, "total mse", round(s["total"]["mse_blend"],2), s["total"]["bets"], [w["w_total"] for w in s["weights"]])
json.dump(out,open(sys.argv[1],"w"))
# wind split for full model under bets
