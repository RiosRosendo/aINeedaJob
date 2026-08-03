import './jobs.css';

export const metadata = {
  title: 'Jobs',
};

export default function JobsLayout({ children }: { children: React.ReactNode }) {
  return (
    <>
      <link href="https://fonts.googleapis.com/css2?family=Caprasimo:wght@400&family=Figtree:wght@400;600;700&display=swap" rel="stylesheet" />
      {children}
    </>
  );
}
