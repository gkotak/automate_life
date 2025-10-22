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
          padding: '0px',
          gap: '24px',
          width: '278px',
          zIndex: 0
        }}
      >
        {/* Logo and brand name - Link */}
        <div
          style={{
            display: 'flex',
            flexDirection: 'row',
            justifyContent: 'center',
            alignItems: 'center',
            padding: '0px',
            gap: '8px',
            height: '40px',
            mixBlendMode: 'normal',
            borderRadius: '0px'
          }}
        >
          {/* Icon */}
          <div
            style={{
              width: '40px',
              height: '40px',
              mixBlendMode: 'normal'
            }}
          >
            <svg width="40" height="40" viewBox="0 0 40 40" fill="none">
              <circle cx="20" cy="20" r="14" fill="#FFFFFF" />
              {[...Array(8)].map((_, i) => {
                const angle = (i * Math.PI) / 4;
                return (
                  <line
                    key={i}
                    x1="20"
                    y1="20"
                    x2={20 + Math.cos(angle) * 15}
                    y2={20 + Math.sin(angle) * 15}
                    stroke="#FFFFFF"
                    strokeWidth="3"
                    strokeLinecap="round"
                  />
                );
              })}
            </svg>
          </div>

          {/* Brand name */}
          <div
            style={{
              fontFamily: 'Manrope, sans-serif',
              fontStyle: 'normal',
              fontWeight: 800,
              fontSize: '28px',
              lineHeight: '32px',
              display: 'flex',
              alignItems: 'center',
              letterSpacing: '-0.56px',
              color: '#FFFFFF'
            }}
          >
            Article Summarizer
          </div>
        </div>

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
          AI-powered article analysis with video and audio content extraction for comprehensive summaries.
        </div>
      </div>
    </div>
  );
}
