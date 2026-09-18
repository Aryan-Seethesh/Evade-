import { NavLink } from 'react-router-dom';

export default function Nav() {
  const links = [
    ['/', 'Operations'],
    ['/scenarios', 'Scenarios'],
    ['/decisions', 'Decisions'],
    ['/analytics', 'Analytics'],
    ['/architecture', 'Architecture'],
  ] as const;
  return (
    <nav className="nav">
      {links.map(([to, label]) => (
        <NavLink key={to} to={to} end={to === '/'} className={({ isActive }) => isActive ? 'nav-link on' : 'nav-link'}>
          {label}
        </NavLink>
      ))}
    </nav>
  );
}
