%% bms_pack_sim.m
% Self-contained pack + simple BMS simulation
% Pack: Ns x Np (series x parallel)
% Cell: Thevenin 1-RC model with OCV(SOC) lookup
% BMS: Coulomb counting, EKF per cell, passive balancing, protection hysteresis

clear; close all; clc;

%% Pack & cell parameters
Ns = 12;   % cells in series
Np = 3;    % parallel strings
Ncell = Ns * Np;

% Nominal cell parameters (arrays for slight cell variation)
Q_ah = 5;               % Ah
Q = Q_ah * 3600;        % Coulombs
R0_nom = 0.05;          % ohm
R1_nom = 0.02;          % ohm (RC)
C1_nom = 2000;          % F (RC capacitance)
mass = 0.045;           % kg
Cp = 900;               % J/kg-K

% Small random variation across cells to simulate imbalance
rng(1);
R0 = R0_nom * (1 + 0.05*randn(Ncell,1));
R1 = R1_nom * (1 + 0.05*randn(Ncell,1));
C1 = C1_nom * (1 + 0.05*randn(Ncell,1));
Capacity = Q * (1 + 0.02*randn(Ncell,1)); % Coulombs per cell variation

% OCV-SOC table (monotonic)
soc_grid = linspace(0,1,11);
ocv_grid = [3.00 3.30 3.45 3.55 3.60 3.65 3.70 3.75 3.90 4.00 4.20]; % V per cell

% Thermal
h_conv = 10;            % W/m2-K (lumped)
area = 0.004;           % m2
Tamb = 298.15;          % K (25C)
T = Tamb * ones(Ncell,1);

% Initial states
SOC_true = 0.95*ones(Ncell,1);     % true SOC per cell
Vrc_true = zeros(Ncell,1);         % RC transient voltage
SOC_ekf = SOC_true + 0.02*randn(Ncell,1); % initial EKF estimates
P_ekf = 1e-4 * eye(2);             % initial covariance (same for all cells)
P_ekf = repmat(P_ekf, [1,1,Ncell]);
Vrc_est = zeros(Ncell,1);          % EKF RC voltage estimate

% Simulation parameters
dt = 1;                % s
Tsim = 3600*2;         % 2 hours
time = 0:dt:Tsim;
Nt = numel(time);

% Drive current profile (pack current): positive = discharge
Ipack = zeros(Nt,1);
Ipack(1:1800) = 10;     % 10 A discharge for 30 min
Ipack(1801:3600) = -5;  % 5 A charge for 30 min
Ipack(3601:end) = 0;

% Pre-allocate logs
Vcell = zeros(Nt,Ncell);
Vpack = zeros(Nt,1);
SOC_log = zeros(Nt,Ncell);
SOC_ekf_log = zeros(Nt,Ncell);
Tlog = zeros(Nt,Ncell);
bal_state = zeros(Nt,Ncell); % 1 = bleed on

% BMS settings
V_max_cell = 4.20;
V_min_cell = 2.70;
V_bal_thresh = 4.05;      % start balancing when above this (during charge)
bal_res = 5;              % ohms bleed resistor when balancing (passive)
bal_hysteresis = 0.01;    % SOC hysteresis (fraction)
temp_max = 323.15;        % 50 C in K
protection_locked = false;

%% Helper inline functions
ocv_from_soc = @(soc) interp1(soc_grid, ocv_grid, max(0,min(1,soc)), 'pchip');

%% Sim loop
for k = 1:Nt
    I = Ipack(k); % pack current (A)
    
    % Compute per-cell current (simple model: each parallel cell sees I/Np)
    Icell = (I / Np) * ones(Ncell,1);
    
    % Apply balancing bleed current
    for c = 1:Ncell
        if bal_state(max(1,k-1),c) == 1
            Icell(c) = Icell(c) + (ocv_from_soc(SOC_true(c)) / bal_res);
        end
    end
    
    % Update true cell model (Thevenin 1-RC)
    V_oc = ocv_from_soc(SOC_true);
    tau = R1 .* C1;
    Vrc_true = Vrc_true .* exp(-dt./tau) + R1 .* (1 - exp(-dt./tau)) .* Icell;
    V_cell = V_oc - Icell .* R0 - Vrc_true;
    
    % Update SOC true
    SOC_true = SOC_true - (Icell * dt) ./ Capacity;
    SOC_true = max(0,min(1,SOC_true));
    
    % Thermal update
    Qgen = (Icell.^2) .* R0; % W per cell
    T = T + (dt ./ (mass * Cp)) .* (Qgen - h_conv*area.*(T - Tamb));
    
    % Log true values
    Vcell(k,:) = V_cell';
    Vseries = zeros(Ns,1);
    for s = 1:Ns
        idx = s:Ns:Ncell;
        Vseries(s) = mean(V_cell(idx));
    end
    Vpack(k) = sum(Vseries);
    SOC_log(k,:) = SOC_true';
    Tlog(k,:) = T';
    
    %% BMS: Measurements
    Vmeas = V_cell + 1e-3*randn(Ncell,1); % V
    Imeas = (I / Np) * ones(Ncell,1) + 1e-3*randn(Ncell,1);
    Tmeas = T + 0.1*randn(Ncell,1);
    
    %% BMS: EKF per cell
    for c = 1:Ncell
        % Predict
        SOC_pred = SOC_ekf(c) - (Imeas(c)*dt) / Capacity(c);
        Vrc_pred = Vrc_est(c) * exp(-dt/(R1(c)*C1(c))) + ...
                   R1(c)*(1 - exp(-dt/(R1(c)*C1(c))))*Imeas(c);
        Vpred = ocv_from_soc(SOC_pred) - Imeas(c)*R0(c) - Vrc_pred;
        
        dOCVdSOC = (ocv_from_soc(min(1,SOC_pred+1e-6)) - ...
                    ocv_from_soc(max(0,SOC_pred-1e-6)))/(2e-6);
        H = [dOCVdSOC, -1];
        F = [1,0;0,exp(-dt/(R1(c)*C1(c)))];
        Qk = diag([1e-7,1e-5]); Rk = 5e-4;
        
        Pprev = P_ekf(:,:,c);
        Ppred = F*Pprev*F' + Qk;
        
        S = H * Ppred * H' + Rk;
        K = Ppred * H' / S;
        
        innov = Vmeas(c) - Vpred;
        xupd = [SOC_pred; Vrc_pred] + K * innov;
        
        SOC_ekf(c) = max(0,min(1,xupd(1)));
        Vrc_est(c) = xupd(2);
        P_ekf(:,:,c) = (eye(2) - K*H) * Ppred;
    end
    SOC_ekf_log(k,:) = SOC_ekf';
    
    %% Balancing logic (passive)
    if I < 0
        for c = 1:Ncell
            if Vmeas(c) >= V_bal_thresh
                bal_state(k,c) = 1;
            else
                if k>1 && bal_state(k-1,c)==1 && Vmeas(c) >= (V_bal_thresh - 0.01)
                    bal_state(k,c) = 1;
                else
                    bal_state(k,c) = 0;
                end
            end
        end
    else
        bal_state(k,:) = 0;
    end
    
    %% Protection checks
    if any(Vmeas > V_max_cell) || any(Vmeas < V_min_cell) || any(Tmeas > temp_max)
        protection_locked = true;
    end
    if protection_locked
        if k < Nt
            Ipack(k+1:end) = 0;
        end
    end
end

%% Plots
figure('Name','Pack summary','Position',[200 200 1000 700]);

subplot(3,2,1);
plot(time/60, Vpack); xlabel('Time (min)'); ylabel('Pack V (V)'); title('Pack Voltage');

subplot(3,2,2);
plot(time/60, mean(Vcell,2)); hold on;
plot(time/60, max(Vcell,[],2),'--');
plot(time/60, min(Vcell,[],2),'--');
xlabel('Time (min)'); ylabel('Cell V (V)');
title('Cell voltages (mean/max/min)'); legend('mean','max','min');

subplot(3,2,3);
plot(time/60, mean(SOC_log,2)); hold on;
plot(time/60, mean(SOC_ekf_log,2),'--');
xlabel('Time (min)'); ylabel('SOC');
title('Mean SOC (true vs EKF)'); legend('true','EKF');

subplot(3,2,4);
imagesc(time/60,1:Ncell,SOC_log'); axis xy; colorbar;
xlabel('Time (min)'); ylabel('Cell index'); title('SOC per cell');

subplot(3,2,5);
plot(time/60, mean(Tlog,2));
xlabel('Time (min)'); ylabel('T (K)'); title('Mean cell temperature');

subplot(3,2,6);
imagesc(time/60,1:Ncell,bal_state'); axis xy; colorbar;
xlabel('Time (min)'); ylabel('Cell index'); title('Balancing state (1=on)');

sgtitle(sprintf('Sim: %ds %dp pack, Protection locked: %d', Ns, Np, protection_locked));

disp('Simulation complete.');