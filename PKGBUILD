# Maintainer: Selachii Project <open-source@hanstech.dev>
pkgname=sven-bin
pkgver=1.1.0
pkgrel=1
pkgdesc="Sven Package Manager for Selachii (LFS) - PyInstaller Binary"
arch=('x86_64')
url="https://github.com/YOUR_USERNAME/fin"
license=('GPL3')
depends=('git' 'gnupg' 'curl' 'tar' 'zstd')
provides=('fin')
conflicts=('fin' 'sven-git')
source=("sven-x86_64-linux::https://github.com/YOUR_USERNAME/fin/releases/download/v${pkgver}/sven-x86_64-linux")
sha256sums=('SKIP') # Use actual sha256 in production or use workflow to inline it

package() {
    # Install binary
    install -Dm755 "${srcdir}/sven-x86_64-linux" "${pkgdir}/usr/local/bin/sven"
    
    # Create required directory structure
    install -dm755 "${pkgdir}/var/lib/fin/installed"
    install -dm755 "${pkgdir}/var/lib/fin/sync"
    install -dm755 "${pkgdir}/var/lib/fin/aur_cache"
    install -dm755 "${pkgdir}/var/lib/fin/snapshots"
    install -dm755 "${pkgdir}/var/cache/fin/pkgs"
    install -dm755 "${pkgdir}/var/cache/fin/aur"
    install -dm755 "${pkgdir}/var/log/fin"
    install -dm755 "${pkgdir}/etc/fin/initscripts"
    install -dm755 "${pkgdir}/tmp/fin/aur"

    # Default config
    cat > "${srcdir}/fin.conf" << 'EOF'
[general]
install_root      = /
cache_dir         = /var/cache/fin
db_path           = /var/lib/fin
init_system       = sysvinit

[repos]
use_official      = true
use_aur           = true
aur_review        = prompt

[build]
parallel_jobs     = 4
keep_cache        = true

[download]
parallel_downloads = 5
mirror             = auto

[upgrade]
ignored_packages  =
held_packages     =
EOF
    install -Dm644 "${srcdir}/fin.conf" "${pkgdir}/etc/fin/fin.conf"
}
