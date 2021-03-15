Raspberry Pi Software
=====================

Auf eine SD-Karte ein [Raspbian](https://www.raspberrypi.org/software/operating-systems/) (Lite -- ohne Desktop) kopieren und den *Raspberry Pi* booten.

Nach dem Anmelden muss via `sudo raspi-config` in *3 Interface Options* unter *P5 I2C* das I²C Kernelmodul aktiviert werden (wird für das Display gebraucht).

Danach müssen die benötigten Pakete für die *ScanStation* (Eingabe via GPIO, Ausgabe via OLED-Display & Scannersteuerung) installiert & natürlich dieses Repo lokal geklont werden:

	sudo apt update
	sudo apt dist-upgrade
	sudo apt install git python3 python3-pip python3-pil libgirepository1.0-dev libcairo2-dev pkg-config python3-dev gir1.2-gtk-3.0 rpi.gpio 

	python3 -m pip install --upgrade pip
	python3 -m pip install pycairo PyGObject luma.oled luma.core

	git clone --recursive https://github.com/thelazt/scanstation.git ~/scanstation


Scanner
-------

Es kann jeder [SANE](https://de.wikipedia.org/wiki/Scanner_Access_Now_Easy)-kompatible Scanner verwendet werden.
Für einen (alten) HP OfficeJet braucht man beispielsweise das Paket `hplip`:

	sudo apt install hplip

	sudo sane-find-scanner
	sudo scanimage -L

	sudo usermod -a -G scanner pi

Sofern `scanimage -L` ohne `sudo` keine Ergebnisse liefert, müssen noch die udev-Regeln angepasst werden. Dazu beispielsweise via `lsusb` für den USB Scanner *HP PSC 1315*

	Bus 001 Device 004: ID 03f0:3f11 HP, Inc PSC-1315/PSC-1317

die Vendor- (hier `03f0`) und Product-ID (`3f11`) herausfinden und eine entsprechende neue Regel erstellen:

	echo 'ATTRS{idVendor}=="03f0", ATTRS{idProduct}=="3f11",  MODE="0666", GROUP="scanner", ENV{libsane_matched}="yes"' > /etc/udev/rules.d/99-libsane.rules
	sudo udevadm control --reload-rules
	sudo udevadm trigger


JBIG2 Encoder
-------------

Die eingescannten Seiten werden im [Portable Document Format (PDF)](https://de.wikipedia.org/wiki/Portable_Document_Format) gespeichert, bei welchem die gescannten Bilder für eine geringe Dateigröße wiederum im [JBIG2](https://de.wikipedia.org/wiki/JBIG2)-Format gespeichert werden.

	sudo apt install autoconf gcc make libtool libleptonica-dev
	cd jbig2enc
	./autogen.sh
	./configure
	make -j 4
	cd ..


libinsane
---------

Die Bibliothek [Libinsane](https://gitlab.gnome.org/World/OpenPaperwork/libinsane) bietet für die Skriptsprache Python einen einfachen Zugriff auf angeschlossene Scanner.
Dafür werden noch einige Buildwerkzeuge und Programmbibliotheken benötigt, es kann wie folgt installiert werden:

	sudo apt install meson cmake libsane-dev gtk-doc-tools valac
	cd libsane
	make
	sudo make install
	cd ..


Paperwork
---------

Für die Verwaltung der Dokumente wird [Paperwork](https://openpaper.work/) verwendet. Das kann über den [Python Paketmanager (pip)](https://de.wikipedia.org/wiki/Pip_(Python)) installiert werden, dazu wird aber die PDF Programmbibliothek [Poppler](https://de.wikipedia.org/wiki/Poppler) sowie die [Texterkennungssoftware (OCR)](https://de.wikipedia.org/wiki/Texterkennung) [Tesseract](https://de.wikipedia.org/wiki/Tesseract_(Software)) benötigt:

	sudo apt install poppler-data libpoppler-dev libpoppler-cpp-dev gir1.2-poppler-0.18 iso-codes tesseract-ocr tesseract-ocr-deu 
	python3 -m pip install paperwork paperwork-shell python-poppler termcolor natsort levenshtein

Die Dokumente (als PDF sowie eine XML Datei mit den OCR Daten) werden von *Paperwork* in das Verzeichnis `~/papers/` importiert.
Dieses Verzeichnis sollte natürlich aufgrund der eher kurzen Lebensdauer von SD-Karten irgendwie gesichert werden.
Sofern ein Netzlaufwerk existiert, kann beispielsweise dieses verwendet werden.

Allerdings ist es auch möglich ein [Git-Repository](https://de.wikipedia.org/wiki/Git) zu verwenden:
Die Binärdateien (Bild im PDF Dokument) haben eine akzeptable Größe und werden i.d.R. nicht mehr verändert, entsprechend ist dieses Versionsverwaltungssystem geeignet:


### Repo auf entfernten Server

Auf einem via SSH erreichbaren Server wird nun ein Git Repository angelegt:

	mkdir papers.git
	cd papers.git
	git init --bare

Natürlich können auch andere Git-Hostingplattformen verwendet werden.


### Repoverzeichnis auf RPi

Zuerst sollte ein SSH Schlüssel erstellt und auf den Server authorisiert werden:

	ssh-keygen
	ssh-copy-id user@example.org

Dann wird das eben erstellte Repo auf den Raspberry Pi geklont:

	git clone ssh://user@example.org:/home/user/papers.git /home/pi/papers
	git config --global user.email "scanstation@example.org"
	git config --global user.name "ScanStation"


### Repoverzeichnis auf Arbeitsrechner

Analog dazu kann auf den PCs, mit welchen diese Dokumente angeschaut (und annotiert) werden sollen, das Repo ebenfalls nach `~/papers` geklont werden. Außerdem empfiehlt es sich hier, [Paperwork gemäß der Anleitung zu installieren](https://gitlab.gnome.org/World/OpenPaperwork/paperwork/#installation) -- bei Linux z.B. via 

	git clone ssh://user@example.org:/home/user/papers.git ~/papers
	echo "*.thumb.jpg" > ~/papers/.gitignore
	flatpak --user install https://builder.openpaper.work/paperwork_master.flatpakref

Vor dem Starten sollten Änderungen (via `git pull`) geholt und nach dem Bearbeiten auf den Arbeitsrechnern natürlich immer wieder zurück geschoben (`git push`) werden - dazu kann auch das Hilfsskript `utils/paperwork.sh` verwendet werden.


Konfiguration
-------------

Die Beispielkonfiguration muss nach `config.ini` kopiert und an die eigenen Bedürfnisse angepasst werden:

	cp config.example.ini config.ini
	nano config.ini


(Auto)Start
-----------

Die Python-Skripte werden via [systemd](https://de.wikipedia.org/wiki/Systemd) gestartet, dazu müssen ggf. die Pfade in der `scanstation.service`-Datei angepasst und diese in das Verzeichnis `/etc/systemd/system/` kopiert werden:

	sudo cp scanstation.service /etc/systemd/system/
	sudo systemctl daemon-reload
	sudo systemctl start scanstation

Die *ScanStation* soll nun auch direkt nach dem Boot automatisch gestartet werden, dazu

	sudo systemctl enable scanstation

ausführen.

