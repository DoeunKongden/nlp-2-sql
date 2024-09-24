import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
from io import BytesIO
import traceback


def execute_plot_code(plot_code: str, results):
    buf = BytesIO()
    try:
        print(f"Executing plot_code: {plot_code}")
        # Execute the plot code in a restricted environment 
        exec_globals = {
            'plt': plt,
            'sns': sns,
            'data': pd.DataFrame(results), # converting the sql query result into Dataframe
        }

        # Execute the AI-generated code
        exec(plot_code, exec_globals)

        # Save figure to buffer 
        if plt.get_fignums():  # check if any figure was generated
            plt.savefig(buf, format='png')
            plt.close('all')
            buf.seek(0)  # Move to start of buffer to return it
            return buf
        else:
            raise "No figure was generated by the plotting code."

    except Exception as e:
        print(f"Error executing plot code : {traceback.format_exc()}")
        raise e
