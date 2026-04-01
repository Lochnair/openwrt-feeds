# SPDX-License-Identifier: GPL-2.0-only
#
# Copyright (C) 2023 Nils Andreas Svee
# Copyright (C) 2026 Fabio Rieker

include $(TOPDIR)/rules.mk

PKG_NAME:=sqm-autorate-rust
PKG_VERSION:=0.1
PKG_RELEASE:=2

PKG_SOURCE_PROTO:=git
PKG_SOURCE_URL:=https://github.com/Lochnair/sqm-autorate-rust
PKG_SOURCE_VERSION:=7d833ecff8b69c12fdcbe5da64c6cfc74b3dc720

PKG_MAINTAINER:=Nils Andreas Svee <me@lochnair.net>
PKG_LICENSE:=MPL

PKG_BUILD_DEPENDS:=rust/host

include $(TOPDIR)/feeds/packages/lang/rust/rust-package.mk
include $(INCLUDE_DIR)/package.mk

define Build/Compile
	$(call Build/Compile/Cargo,,)
endef

define Package/sqm-autorate-rust
	SECTION:=utils
	CATEGORY:=Utilities
	TITLE:=sqm autorate (rust)
	DEPENDS:=$(RUST_ARCH_DEPENDS)
	URL:=https://github.com/Lochnair/sqm-autorate-rust
endef

define Package/sqm-autorate-rust/description
  Rust port of the Lua implementation of CAKE autorate
endef

define Package/sqm-autorate-rust/install
	# 2. Fix the path for the new standard rust behaviour: Point to 'release' instead of 'stripped'
	$(INSTALL_DIR) $(1)/usr/sbin
	$(INSTALL_BIN) $(PKG_BUILD_DIR)/target/$(RUSTC_TARGET_ARCH)/release/sqm-autorate-rust $(1)/usr/sbin/sqm-autorate-rust

	# Create necessary configuration and state directories
	$(INSTALL_DIR) $(1)/etc/init.d
	$(INSTALL_DIR) $(1)/etc/config
	$(INSTALL_DIR) $(1)/etc/sqm-autorate
	$(INSTALL_DIR) $(1)/usr/share/sqm-autorate

	# Install init and update scripts (chmod 755)
	$(INSTALL_BIN) ./files/sqm-autorate.init $(1)/etc/init.d/sqm-autorate
	$(INSTALL_BIN) ./files/sqm-autorate-update.sh $(1)/usr/sbin/sqm-autorate-update

	# Install sample config (chmod 600)
	$(INSTALL_CONF) ./files/sqm-autorate.sample $(1)/etc/config/sqm-autorate.sample

	# Install ROM fallback data (chmod 644)
	$(INSTALL_DATA) $(PKG_BUILD_DIR)/reflectors-icmp.csv $(1)/usr/share/sqm-autorate/reflectors-icmp.csv

	# Create the symlink the Rust binary expects (points to RAM)
	ln -sf /tmp/reflectors-icmp.csv $(1)/etc/sqm-autorate/reflectors-icmp.csv
endef

$(eval $(call BuildPackage,sqm-autorate-rust))