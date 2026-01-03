# [replace begin]
import base64
import os
from io import BytesIO

# before importing matplotlib
# to avoid the wasm backend (which needs js.document', not available in worker)
os.environ["MPLBACKEND"] = "AGG"

import matplotlib.pyplot

_old_show = matplotlib.pyplot.show
assert _old_show, "matplotlib.pyplot.show"


def show(*, block=None):
    buf = BytesIO()
    matplotlib.pyplot.savefig(buf, format="png")
    buf.seek(0)
    # encode to a base64 str
    img_str = base64.b64encode(buf.read()).decode("utf-8")
    matplotlib.pyplot.clf()
    buf.close()
    print(f"data:image/png;base64,{img_str}")


matplotlib.pyplot.show = show
# [replace end]
