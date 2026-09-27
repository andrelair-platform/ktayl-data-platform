import type {SidebarsConfig} from '@docusaurus/plugin-content-docs';

const sidebars: SidebarsConfig = {
  docs: [
    {type: 'doc', id: 'intro', label: 'Overview'},
    {
      type: 'category',
      label: 'Architecture & Design',
      collapsed: false,
      items: [
        {type: 'doc', id: 'architecture', label: 'Architecture'},
        {type: 'doc', id: 'system-design', label: 'System Design'},
        {type: 'doc', id: 'design-patterns', label: 'Design Patterns'},
      ],
    },
    {type: 'doc', id: 'data-model', label: 'Data Model'},
  ],
};

export default sidebars;
