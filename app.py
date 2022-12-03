from pathlib import Path

import matplotlib as mpl
from matplotlib import ticker
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
    ui.br(),
    ui.layout_sidebar(
        ui.panel_sidebar(
            ui.markdown(next(Path(".").rglob("README.md")).read_text("utf-8")),
            ui.input_text_area("text", "Text to analyze"),
            ui.input_text("words", "Words to find in text"),
            ui.row(
                ui.input_checkbox("icase", "Ignore case"),
                ui.input_checkbox("regex", "Regular expressions"),
            ),
        ),
        ui.panel_main(
            ui.output_plot("dispersion_plot"),
            ui.output_table("freq_dist"),
        ),
    ),
    title="Lexical dispersion plot",
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
    def tokenize_text():
        text = input.text().strip()
        if not text:
            warn("no-text", "Please provide an input text.")
            return []
        ui.notification_remove("no-text")
        if input.icase():
            text = text.lower()
        return tokenize(text)

    @reactive.Calc
    def word2y():
        words = input.words().strip()
        if not words:
            warn("no-words", "Please provide words to plot.")
            return {}
        ui.notification_remove("no-words")
        icase = ""
        if input.icase():
            if input.regex():
                icase = "(?i)"
            else:
                words = words.lower()
        return {f"{icase}{w}": i for (i, w) in enumerate(reversed(words.split()))}

    @reactive.Calc
    def analyze():
        text = tokenize_text()
        words = word2y()
        if not (text and words):
            return

        if input.regex():

            def match(tok, words):
                # Doing a nested loop for each token is sort of inefficient, but it will
                # do for a demo. Plus NLTK's too-functional-for-its-own-good
                # implementation of dispersion plot does the same for non-regex
                # matching, where it's blatantly unnecessary (see other match function
                # below), so...
                for word in words:
                    if re.fullmatch(word, tok):
                        return word

        else:

            def match(tok, words):
                if tok in words:
                    return tok

        xs = []
        ys = []
        freq_dist = {w: 0 for w in words}
        for x, tok in enumerate(text):
            if (word := match(tok, words)) is not None:
                xs.append(x)
                ys.append(words[word])
                freq_dist[word] += 1
        if not (xs and ys):
            warn("no-result", "None of the words were found.")
            return
        ui.notification_remove("no-result")

        return xs, ys, freq_dist

    @output
    @render.plot(alt="Dispersion plot of chosen words in input text")
    def dispersion_plot():
        if (analysis := analyze()) is None:
            return
        xs, ys, freq_dist = analysis
        fig, [[ax]] = plt.subplots(squeeze=False)
        ax.plot(xs, ys, marker="|", markersize=20, linestyle="")
        ax.set_xlabel("Word offset")
        ax.xaxis.set_major_formatter(ticker.StrMethodFormatter("{x:,.0f}"))
        ax.set_yticks(range(len(freq_dist)), labels=list(freq_dist))
        ax.set_ylim(-1, len(freq_dist))
        ax.tick_params(axis="both", length=0)
        return fig

    @output
    @render.table()
    def freq_dist():
        if (analysis := analyze()) is None:
            return
        _, _, freq_dist = analysis
        df = pd.DataFrame(freq_dist.items(), columns=["word", "frequency"]).sort_values(
            ["frequency", "word"], ascending=False
        )
        return df


app = App(app_ui, server)
