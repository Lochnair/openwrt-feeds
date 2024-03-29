#
# Copyright (C) 2007-2014 OpenWrt.org
#
# This is free software, licensed under the GNU General Public License v2.
# See /LICENSE for more information.
#

include $(TOPDIR)/rules.mk

PKG_NAME:=luajit-lanes
PKG_VERSION:=3.16.2
PKG_RELEASE:=1

PKG_SOURCE:=$(PKG_NAME)-$(PKG_VERSION).tar.gz
PKG_SOURCE_URL:=https://codeload.github.com/LuaLanes/lanes/tar.gz/v$(PKG_VERSION)?
PKG_HASH:=3af9e599877b7d41dea03a0180ad48c77ed324564ecb08a6e3b8d63612944194
PKG_BUILD_DIR:=$(BUILD_DIR)/lanes-$(PKG_VERSION)

PKG_INSTALL:=1
PKG_BUILD_PARALLEL:=1

PKG_BUILD_DEPENDS:=lua/host

include $(INCLUDE_DIR)/package.mk

define Package/luajit-lanes
	SUBMENU:=Lua
	SECTION:=lang
	CATEGORY:=Languages
	TITLE:=LuaLanes
	URL:=http://lualanes.github.io/lanes/
	DEPENDS:=+luajit +liblua +libpthread
	MAINTAINER:=Vladimir Malyutin <first-leon@yandex.ru>
endef

define Package/luajit-lanes/description
 Lua Lanes is a Lua extension library providing the possibility to run
multiple Lua states in parallel. It is intended to be used for optimizing
performance on multicore CPU's and to study ways to make Lua programs
naturally parallel to begin with.

Lanes is included into your software by the regular require "lanes" method.
No C side programming is needed; all APIs are Lua side, and most existing
extension modules should work seamlessly together with the multiple lanes.

Lanes supports Lua 5.1, 5.2 and 5.3
endef

define Build/Compile
	$(MAKE) -C $(PKG_BUILD_DIR) all \
        CC="$(TARGET_CC)" \
        LUA="$(STAGING_DIR_HOSTPKG)/bin/luajit" \
	LUA_FLAGS="-I$(STAGING_DIR)/usr/include -I$(STAGING_DIR)/usr/include/luajit-2.1/"
	LUA_LIBS=-lluajit-5.1
endef

define Package/luajit-lanes/install
	$(INSTALL_DIR) $(1)/usr/lib/lua
	$(INSTALL_BIN) $(PKG_BUILD_DIR)/src/lanes.lua $(1)/usr/lib/lua/
	$(INSTALL_DIR) $(1)/usr/lib/lua/lanes
	$(INSTALL_DATA) $(PKG_BUILD_DIR)/src/lanes/core.so $(1)/usr/lib/lua/lanes/core.so
endef

$(eval $(call BuildPackage,luajit-lanes))
