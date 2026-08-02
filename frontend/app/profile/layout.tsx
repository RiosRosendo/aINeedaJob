import './profile.css';

export default function ProfileLayout({ children }: { children: React.ReactNode }) {
  return (
    <>
      <link href="https://fonts.googleapis.com/css2?family=Caprasimo&family=Figtree:wght@400;500;600;700&display=swap" rel="stylesheet" />
      {children}
    </>
  );
}
