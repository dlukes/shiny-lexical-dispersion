from collections import Counter

import matplotlib as mpl
import matplotlib.pyplot as plt
import pandas as pd
import regex as re
from shiny import App, reactive, render, ui

# We don't use Jinja2 directly in the app, but without the import, shinylive currently
# doesn't bundle Jinja2's wheel and the library therefore fails to load.
import jinja2

mpl.rcParams.update(
    {
        "figure.dpi": 300,
        "axes.grid": True,
        "axes.grid.axis": "both",
        "grid.color": "gainsboro",
        "axes.spines.left": False,
        "axes.spines.right": False,
        "axes.spines.top": False,
        "axes.spines.bottom": False,
    }
)

app_ui = ui.page_fluid(
    ui.panel_title("Lexical dispersion plot"),
    ui.layout_sidebar(
        ui.panel_sidebar(
            ui.input_text_area("text", "Text to analyze"),
            ui.input_text("words", "Space-separated words to plot"),
            ui.input_checkbox("icase", "Ignore case"),
        ),
        ui.panel_main(
            ui.output_plot("dispersion_plot"),
            ui.output_table("freq_dist"),
        ),
    ),
)


def tokenize(text):
    return re.findall(
        r"\p{Alphabetic}+(?:\S+\p{Alphabetic}+)*|[\S&&\P{Alphabetic}]+",
        text,
        flags=re.VERSION1,
    )


def warn(id, msg, **notification_show_kwargs):
    # NOTE: duration=None should leave the notification around indefinitely, but
    # currently doesn't, see https://github.com/rstudio/py-shiny/issues/257
    ui.notification_show(
        **notification_show_kwargs, ui=msg, id=id, type="warning", duration=None
    )


def server(input, output, session):
    @reactive.Calc
    def tokenized_text():
        text = input.text().strip()
        if not text:
            warn("no-text", "Please provide an input text.")
            return []
        ui.notification_remove("no-text")
        if input.icase():
            text = text.lower()
        return tokenize(text)

    @reactive.Calc
    def split_words():
        words = input.words().strip()
        if not words:
            warn("no-words", "Please provide words to plot.")
            return {}
        ui.notification_remove("no-words")
        if input.icase():
            words = words.lower()
        return {w: i for (i, w) in enumerate(reversed(words.split()))}

    @output
    @render.plot(alt="Dispersion plot of chosen words in input text")
    def dispersion_plot():
        text = tokenized_text()
        words = split_words()
        if not (text and words):
            return

        xs = []
        ys = []
        for i, tok in enumerate(text):
            if tok in words:
                xs.append(i)
                ys.append(words[tok])
        if not (xs and ys):
            warn("no-plot", "None of the words were found.")
            return
        ui.notification_remove("no-plot")

        fig, ax = plt.subplots()
        ax.plot(xs, ys, marker="|", markersize=20, linestyle="")
        ax.set_yticks(range(len(words)), labels=list(words))
        ax.tick_params(axis="both", length=0)
        ax.set_xlabel("Word offset")
        return fig

    @output
    @render.table()
    def freq_dist():
        text = tokenized_text()
        words = set(split_words())
        if not (text and words):
            return

        freq_dist = Counter(t for t in text if t in words)
        for w in words:
            if w not in freq_dist:
                freq_dist[w] = 0
        df = pd.DataFrame(freq_dist.most_common(), columns=["word", "frequency"])
        return df


app = App(app_ui, server)
