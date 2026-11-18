type DisclaimerProps = { className?: string };

export function Disclaimer({ className }: DisclaimerProps) {
  return (
    <p className={className}>Cet outil ne fournit aucun conseil juridique.</p>
  );
}
