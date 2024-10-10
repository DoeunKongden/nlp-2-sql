import logging
import matplotlib.pyplot as plt
import seaborn as sns
from io import BytesIO
import traceback

logger = logging.getLogger(__name__)


def execute_plot_code(plot_code: str, results):
    """
        Executes the AI-generated Python plot code, passes the SQL result data, and returns the generated plot as a buffer.

        Args:
            plot_code (str): The Python code generated by the AI to create the plot.
            results (list[dict]): The SQL result data passed to the plot code.

        Returns:
            BytesIO: A buffer containing the plot image in PNG format, or None if there was an error.
    """
    buf = BytesIO()
    try:
        # Convert results to a format that the plot code expects
        result = results  # Rename `results` to `result` for compatibility with the AI-generated code

        if not result or len(result) == 0:
            raise ValueError("No data available for plotting.")

        logger.info(f"Data Columns for plotting: {list(result[0].keys())}")  # Log the data columns for reference

        # Set up execution environment and pass the results as `result`
        exec_globals = {
            'plt': plt,
            'sns': sns,
            'result': result  # Pass `result` which the AI-generated code expects
        }

        # Attempt to execute the AI-generated plot code
        logger.info(f"Executing AI-generated plot code:\n{plot_code}")
        exec(plot_code, exec_globals)  # Run the plot code in a controlled environment

        # Check if a figure has been created and save it to a buffer
        if plt.get_fignums():  # Check if any figure was generated
            plt.savefig(buf, format='png')  # Save the figure to the buffer
            plt.close('all')  # Close the plot to free up resources
            buf.seek(0)  # Move to the start of the buffer
            return buf  # Return the buffer containing the plot image

        else:
            raise Exception("No figure was generated by the plotting code.")

    except Exception as e:
        # Log the detailed traceback for debugging
        error_trace = traceback.format_exc()
        logger.error(f"Error while executing plot code: {str(e)}\nTraceback: {error_trace}")
        return None  # Return None in case of failure
