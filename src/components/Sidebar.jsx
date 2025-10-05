import React from 'react'
import SidebarItem from './SidebarItem.jsx'
import { ImageIcon, Film, Type, Settings, PanelLeftClose, PanelLeftOpen } from 'lucide-react'

export default function Sidebar({ items, activeKey, collapsed, onToggleCollapse, onSelect }) {
  return (
    <div className={`h-full ${collapsed ? 'w-16' : 'w-56'} bg-gray-900 border-r border-gray-800 p-3 flex flex-col gap-3 transition-all`}>
      <div className="flex items-center justify-between">
        {!collapsed && <div className="text-sm font-semibold text-gray-200">Brousla</div>}
        <button
          className="p-2 rounded-md hover:bg-gray-800 text-gray-300"
          onClick={onToggleCollapse}
          title={collapsed ? 'Expand' : 'Collapse'}
        >
          {collapsed ? <PanelLeftOpen className="h-4 w-4" /> : <PanelLeftClose className="h-4 w-4" />}
        </button>
      </div>

      <div className="flex-1 space-y-1">
        {items.map(item => (
          <SidebarItem
            key={item.key}
            icon={item.icon}
            label={item.label}
            active={activeKey === item.key}
            collapsed={collapsed}
            onClick={() => onSelect(item.key)}
          />
        ))}
      </div>

      <div className="text-[10px] text-gray-500 text-center">v{window.electron?.appVersion || ''}</div>
    </div>
  )
}


