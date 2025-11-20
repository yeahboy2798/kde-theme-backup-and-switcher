# 1. make py executable
chmod +x kde_theme_gui.py

# 2. Replace in deb tree
cp kde_theme_gui.py deb-build/usr/lib/kde-theme-backup/kde_theme_gui.py
chmod +x deb-build/usr/lib/kde-theme-backup/kde_theme_gui.py

dpkg-deb --build deb-build
mv deb-build.deb installer.deb
sudo dpkg -i installer.deb
