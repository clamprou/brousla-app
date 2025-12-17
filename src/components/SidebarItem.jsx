import React from 'react'

export default function SidebarItem({ icon: Icon, label, active, collapsed, onClick }) {
  return (
    <button
      onClick={onClick}
      className={`w-full flex items-center gap-3 px-3 py-2 rounded-md transition-colors
        ${active ? 'bg-gray-800 text-white' : 'text-gray-300 hover:bg-gray-800/60 hover:text-white'}`}
      title={collapsed ? label : undefined}
    >
      <Icon className="h-5 w-5" />
      {!collapsed && <span className="text-sm font-medium">{label}</span>}
    </button>
  )}


