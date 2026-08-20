# SPDX-License-Identifier: GPL-2.0-only
#
# Copyright (C) 2026 Nils Andreas Svee

include $(TOPDIR)/rules.mk

PKG_NAME:=irtt-rs
PKG_VERSION:=0.6.0
PKG_RELEASE:=1

PKG_SOURCE_PROTO:=git
PKG_SOURCE_URL:=https://github.com/Lochnair/irtt-rs.git
PKG_SOURCE_VERSION:=0e230171008fd9ffce9e6168328b015e7f4ded42

PKG_MAINTAINER:=Nils Andreas Svee <me@lochnair.net>
PKG_LICENSE:=Apache-2.0
PKG_LICENSE_FILES:=LICENSE.txt

PKG_BUILD_DEPENDS:=rust/host

MAKE_PATH:=crates/irtt-app

include $(INCLUDE_DIR)/package.mk
include $(TOPDIR)/feeds/packages/lang/rust/rust-package.mk

CARGO_PKG_ARGS += --no-default-features --bin irtt-rs

ifeq ($(BUILD_VARIANT),client)
  RUST_PKG_FEATURES:=client
endif

ifeq ($(BUILD_VARIANT),full)
  RUST_PKG_FEATURES:=client,server,tui
endif

define Package/irtt-rs/Default
  SECTION:=net
  CATEGORY:=Network
  DEPENDS:=$(RUST_ARCH_DEPENDS)
  URL:=https://github.com/Lochnair/irtt-rs
endef

define Package/irtt-rs
$(call Package/irtt-rs/Default)
  TITLE:=IRTT-compatible Rust client
  VARIANT:=client
  DEFAULT_VARIANT:=1
endef

define Package/irtt-rs/description
  IRTT-compatible Rust client for precise network latency measurements.
endef

define Package/irtt-rs-full
$(call Package/irtt-rs/Default)
  TITLE:=IRTT-compatible Rust client, server, and terminal UI
  VARIANT:=full
  PROVIDES:=irtt-rs
endef

define Package/irtt-rs-full/description
  IRTT-compatible Rust client, server, and terminal UI for network latency
  measurement and testing.
endef

define Package/irtt-rs/install
	$(INSTALL_DIR) $(1)/usr/bin
	$(INSTALL_BIN) $(PKG_INSTALL_DIR)/bin/irtt-rs $(1)/usr/bin/irtt-rs
	$(LN) irtt-rs $(1)/usr/bin/irtt-client
endef

define Package/irtt-rs-full/install
	$(INSTALL_DIR) $(1)/usr/bin
	$(INSTALL_BIN) $(PKG_INSTALL_DIR)/bin/irtt-rs $(1)/usr/bin/irtt-rs
	$(LN) irtt-rs $(1)/usr/bin/irtt-client
	$(LN) irtt-rs $(1)/usr/bin/irtt-server
	$(LN) irtt-rs $(1)/usr/bin/irtt-tui
endef

$(eval $(call BuildPackage,irtt-rs))
$(eval $(call BuildPackage,irtt-rs-full))
