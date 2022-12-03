.PHONY: export deploy clean serve

generated := app.json edit/ index.html shinylive/ shinylive-sw.js

export: clean
	shinylive export . site
	mv -t . site/*
	rmdir site

deploy: export
	git branch -D deploy
	git checkout -b deploy
	git add $(generated)
	git commit -m Deploy
	git push --force-with-lease -u origin deploy
	git checkout master

clean:
	rm -rf $(generated)

serve:
	python3 -m http.server --bind localhost 8008
