export default function BrandPanel() {
  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'center',
        alignItems: 'center',
        padding: '24px 0px',
        gap: '10px',
        isolation: 'isolate',
        width: '364px',
        height: '558px',
        background: 'linear-gradient(341.66deg, #077331 0.8%, #659E7B 96.62%)',
        borderRadius: '24px',
        position: 'relative',
        overflow: 'hidden'
      }}
    >
      {/* Decorative Vector - bottom right */}
      <div
        style={{
          position: 'absolute',
          width: '226.29px',
          height: '142.5px',
          left: '143px',
          top: '361.5px',
          background: 'rgba(255, 255, 255, 0.3)',
          transform: 'rotate(-32deg)',
          zIndex: 1
        }}
      />

      {/* Decorative Vector - top left */}
      <div
        style={{
          position: 'absolute',
          width: '122.9px',
          height: '77.39px',
          left: '-50px',
          top: '-31.5px',
          background: 'rgba(255, 255, 255, 0.3)',
          transform: 'rotate(150deg)',
          zIndex: 2
        }}
      />

      {/* Content - Frame 9 */}
      <div
        style={{
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          padding: '0px',
          gap: '24px',
          width: '278px',
          zIndex: 0
        }}
      >
        {/* Particles Logo */}
        <img
          src="/particles_logo_white.svg"
          alt="Particles"
          style={{
            height: '60px',
            width: 'auto'
          }}
        />

        {/* Value proposition - Supporting text */}
        <div
          style={{
            width: '278px',
            fontFamily: 'Inter, sans-serif',
            fontStyle: 'normal',
            fontWeight: 500,
            fontSize: '16px',
            lineHeight: '24px',
            textAlign: 'center',
            color: '#FFFFFF'
          }}
        >
          Transform articles into actionable insights with AI-powered analysis
        </div>
      </div>
    </div>
  );
}
