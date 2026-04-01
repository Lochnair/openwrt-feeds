#
# Copyright (C) 2007-2014 OpenWrt.org
#
# This is free software, licensed under the GNU General Public License v2.
# See /LICENSE for more information.
#

include $(TOPDIR)/rules.mk

PKG_NAME:=luajit2-lanes
PKG_VERSION:=3.17.2
PKG_RELEASE:=1

PKG_SOURCE:=$(PKG_NAME)-$(PKG_VERSION).tar.gz
PKG_SOURCE_URL:=https://codeload.github.com/LuaLanes/lanes/tar.gz/v$(PKG_VERSION)?
PKG_HASH:=854c1379cde584dd544a3cf098e0ec130248f3a102f65f1064974872e5b4821a
PKG_BUILD_DIR:=$(BUILD_DIR)/lanes-$(PKG_VERSION)

PKG_MAINTAINER:=Vladimir Malyutin <first-leon@yandex.ru>
PKG_LICENSE:=BSD-3-Clause
PKG_LICENSE_FILES:=COPYRIGHT

PKG_BUILD_DEPENDS:=lua/host

include $(INCLUDE_DIR)/package.mk
include $(INCLUDE_DIR)/cmake.mk

define Package/luajit2-lanes
	SUBMENU:=Lua
	SECTION:=lang
	CATEGORY:=Languages
	TITLE:=LuaLanes (LuaJIT2)
	URL:=http://lualanes.github.io/lanes/
	DEPENDS:=+luajit2 +libpthread
endef

define Package/luajit2-lanes/description
Lua Lanes is a Lua extension library providing the possibility to run
multiple Lua states in parallel. It is intended to be used for optimizing
performance on multicore CPU's and to study ways to make Lua programs
naturally parallel to begin with.

This package is built against LuaJIT2 and installs to /usr/lib/luajit2
to avoid conflicts with the standard lualanes package.

Lanes supports Lua 5.1, 5.2 and 5.3
endef

CMAKE_OPTIONS += \
	-DLUA_INCLUDE_DIR=$(STAGING_DIR)/usr/include/luajit-2.1 \
	-DLUA_LIBRARY=$(STAGING_DIR)/usr/lib/libluajit-5.1.so

define Package/luajit2-lanes/install
	$(INSTALL_DIR) $(1)/usr/lib/luajit2
	$(INSTALL_BIN) $(PKG_INSTALL_DIR)/usr/share/lua/lmod/lanes.lua $(1)/usr/lib/luajit2/
	$(INSTALL_DIR) $(1)/usr/lib/luajit2/lanes
	$(INSTALL_DATA) $(PKG_INSTALL_DIR)/usr/share/lua/cmod/core.so $(1)/usr/lib/luajit2/lanes/core.so
endef

$(eval $(call BuildPackage,luajit2-lanes))
