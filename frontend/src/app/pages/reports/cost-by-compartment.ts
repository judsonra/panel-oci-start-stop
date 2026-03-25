import { CommonModule } from '@angular/common';
import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { finalize } from 'rxjs';
import { ButtonModule } from 'primeng/button';
import { CardModule } from 'primeng/card';
import { MessageModule } from 'primeng/message';
import { TableModule } from 'primeng/table';
import { TagModule } from 'primeng/tag';
import { ApiService } from '@/app/core/api.service';
import { CostByCompartmentReportModel, ReportCompartmentCostModel, ReportResourceCostModel } from '@/app/core/models';

interface MonthOption {
    label: string;
    value: number;
}

@Component({
    selector: 'app-cost-by-compartment-page',
    standalone: true,
    imports: [CommonModule, ButtonModule, CardModule, MessageModule, TableModule, TagModule],
    template: `
        <section class="page-header">
            <div>
                <span class="section-kicker">Dashboard</span>
                <h2>Custo por compartimento</h2>
                <p>Consulte o cache local por mês/ano e atualize manualmente os custos da OCI quando precisar renovar os dados.</p>
            </div>
        </section>

        @if (feedback()) {
            <p-message [severity]="feedbackSeverity()" [text]="feedback() || ''"></p-message>
        }

        <section class="page-grid two-columns reports-overview-grid">
            <p-card header="Consulta do período">
                <div class="reports-filter-grid">
                    <label>
                        <span>Mês</span>
                        <select [value]="selectedMonth()" (change)="setSelectedMonth($any($event.target).value)">
                            @for (month of monthOptions; track month.value) {
                                <option [value]="month.value">{{ month.label }}</option>
                            }
                        </select>
                    </label>

                    <label>
                        <span>Ano</span>
                        <input type="number" [value]="selectedYear()" min="2020" max="2100" (input)="setSelectedYear($any($event.target).value)" />
                    </label>
                </div>

                <div class="form-actions reports-actions">
                    <button pButton type="button" label="Consultar" icon="pi pi-search" [disabled]="loading()" (click)="loadReport()"></button>
                    <button pButton type="button" label="Atualizar da OCI" icon="pi pi-refresh" severity="secondary" [disabled]="refreshing()" (click)="refreshReport()"></button>
                    <a pButton [href]="csvUrl()" target="_blank" rel="noopener" label="Exportar CSV" icon="pi pi-download" severity="contrast"></a>
                </div>
            </p-card>

            <p-card header="Resumo do período">
                <div class="summary-list report-meta-list">
                    <div class="summary-row">
                        <span>Origem</span>
                        <p-tag [severity]="report()?.source === 'oci' ? 'warn' : 'success'" [value]="report()?.source === 'oci' ? 'oci' : 'cache'"></p-tag>
                    </div>
                    <div class="summary-row">
                        <span>Última atualização</span>
                        <strong>{{ report()?.last_refreshed_at ? (report()?.last_refreshed_at | date: 'dd/MM/yyyy HH:mm:ss') : 'Sem cache' }}</strong>
                    </div>
                    <div class="summary-row">
                        <span>Moeda</span>
                        <strong>{{ report()?.currency || '-' }}</strong>
                    </div>
                    <div class="summary-row">
                        <span>Total mensal</span>
                        <strong>{{ formatMoney(report()?.total_amount || 0) }}</strong>
                    </div>
                </div>
            </p-card>
        </section>

        @if (loading() || refreshing()) {
            <p-card>
                <p>Consultando dados do relatório...</p>
            </p-card>
        } @else if (!report()?.available) {
            <p-card>
                <p>Nenhum cache encontrado para o período selecionado. Use “Atualizar da OCI” para armazenar o mês no banco local.</p>
            </p-card>
        } @else {
            <section class="stats-grid reports-stats-grid">
                <p-card>
                    <div class="stat-card">
                        <span class="stat-label">Compartimentos</span>
                        <strong>{{ report()?.compartments?.length || 0 }}</strong>
                        <small>Com custo registrado no mês</small>
                    </div>
                </p-card>
                <p-card>
                    <div class="stat-card">
                        <span class="stat-label">Dias com custo</span>
                        <strong>{{ report()?.daily_totals?.length || 0 }}</strong>
                        <small>Série diária armazenada no cache</small>
                    </div>
                </p-card>
                <p-card>
                    <div class="stat-card">
                        <span class="stat-label">Itens detalhados</span>
                        <strong>{{ flattenedResources().length }}</strong>
                        <small>Serviços, SKUs e recursos agregados</small>
                    </div>
                </p-card>
            </section>

            <section class="dashboard-grid report-grid-stack">
                <p-card header="Totais por compartimento">
                    <p-table [value]="report()?.compartments || []" responsiveLayout="scroll">
                        <ng-template pTemplate="header">
                            <tr>
                                <th>Compartimento</th>
                                <th>Total do mês</th>
                                <th>Recursos/serviços</th>
                            </tr>
                        </ng-template>
                        <ng-template pTemplate="body" let-compartment>
                            <tr>
                                <td>{{ compartment.compartment_name || compartment.compartment_id || 'Compartimento não informado' }}</td>
                                <td>{{ formatMoney(compartment.total_amount) }}</td>
                                <td>{{ compartment.resources.length }}</td>
                            </tr>
                        </ng-template>
                    </p-table>
                </p-card>

                <p-card header="Custos diários do mês">
                    <p-table [value]="report()?.daily_totals || []" responsiveLayout="scroll">
                        <ng-template pTemplate="header">
                            <tr>
                                <th>Data</th>
                                <th>Total</th>
                            </tr>
                        </ng-template>
                        <ng-template pTemplate="body" let-day>
                            <tr>
                                <td>{{ day.date | date: 'dd/MM/yyyy':'UTC' }}</td>
                                <td>{{ formatMoney(day.amount) }}</td>
                            </tr>
                        </ng-template>
                    </p-table>
                </p-card>
            </section>

            <section class="page-grid report-detail-grid">
                <p-card header="Composição do custo">
                    <p-table [value]="flattenedResources()" responsiveLayout="scroll">
                        <ng-template pTemplate="header">
                            <tr>
                                <th>Compartimento</th>
                                <th>Serviço</th>
                                <th>SKU</th>
                                <th>Recurso</th>
                                <th>Total</th>
                            </tr>
                        </ng-template>
                        <ng-template pTemplate="body" let-item>
                            <tr>
                                <td>{{ item.compartment_name }}</td>
                                <td>{{ item.service || '-' }}</td>
                                <td>{{ item.sku_name || '-' }}</td>
                                <td>{{ item.resource_name || item.resource_id || '-' }}</td>
                                <td>{{ formatMoney(item.total_amount) }}</td>
                            </tr>
                        </ng-template>
                    </p-table>
                </p-card>
            </section>
        }
    `
})
export class CostByCompartmentPage implements OnInit {
    private readonly api = inject(ApiService);
    private readonly now = new Date();

    readonly report = signal<CostByCompartmentReportModel | null>(null);
    readonly loading = signal(false);
    readonly refreshing = signal(false);
    readonly feedback = signal<string | null>(null);
    readonly feedbackSeverity = signal<'success' | 'error'>('success');
    readonly selectedMonth = signal(this.now.getMonth() + 1);
    readonly selectedYear = signal(this.now.getFullYear());
    readonly csvUrl = computed(() => this.api.getCostByCompartmentCsvUrl(this.selectedYear(), this.selectedMonth()));
    readonly flattenedResources = computed(() => this.flattenResources(this.report()?.compartments || []));

    readonly monthOptions: MonthOption[] = [
        { label: 'Janeiro', value: 1 },
        { label: 'Fevereiro', value: 2 },
        { label: 'Março', value: 3 },
        { label: 'Abril', value: 4 },
        { label: 'Maio', value: 5 },
        { label: 'Junho', value: 6 },
        { label: 'Julho', value: 7 },
        { label: 'Agosto', value: 8 },
        { label: 'Setembro', value: 9 },
        { label: 'Outubro', value: 10 },
        { label: 'Novembro', value: 11 },
        { label: 'Dezembro', value: 12 }
    ];

    ngOnInit(): void {
        this.loadReport();
    }

    setSelectedMonth(value: string | number): void {
        const parsed = Number(value);
        if (parsed >= 1 && parsed <= 12) {
            this.selectedMonth.set(parsed);
        }
    }

    setSelectedYear(value: string | number): void {
        const parsed = Number(value);
        if (Number.isFinite(parsed) && parsed >= 2020) {
            this.selectedYear.set(parsed);
        }
    }

    loadReport(): void {
        this.feedback.set(null);
        this.loading.set(true);
        this.api
            .getCostByCompartment(this.selectedYear(), this.selectedMonth())
            .pipe(finalize(() => this.loading.set(false)))
            .subscribe({
                next: (report) => {
                    this.report.set(report);
                    if (!report.available) {
                        this.feedbackSeverity.set('success');
                        this.feedback.set('Período consultado no banco local. Ainda não há cache para esse mês.');
                    }
                },
                error: (response: { error?: { detail?: string } }) => {
                    this.feedbackSeverity.set('error');
                    this.feedback.set(response.error?.detail ?? 'Não foi possível consultar o relatório salvo.');
                }
            });
    }

    refreshReport(): void {
        this.feedback.set(null);
        this.refreshing.set(true);
        this.api
            .refreshCostByCompartment({ year: this.selectedYear(), month: this.selectedMonth() })
            .pipe(finalize(() => this.refreshing.set(false)))
            .subscribe({
                next: (report) => {
                    this.report.set(report);
                    this.feedbackSeverity.set('success');
                    this.feedback.set('Cache do período atualizado com dados mais recentes da OCI.');
                },
                error: (response: { error?: { detail?: string } }) => {
                    this.feedbackSeverity.set('error');
                    this.feedback.set(response.error?.detail ?? 'Não foi possível atualizar o relatório na OCI.');
                }
            });
    }

    formatMoney(value: number): string {
        const currency = this.report()?.currency || 'USD';
        return new Intl.NumberFormat('pt-BR', {
            style: 'currency',
            currency,
            minimumFractionDigits: 2,
            maximumFractionDigits: 2
        }).format(value);
    }

    private flattenResources(compartments: ReportCompartmentCostModel[]): Array<ReportResourceCostModel & { compartment_name: string }> {
        return compartments.flatMap((compartment) =>
            compartment.resources.map((resource) => ({
                ...resource,
                compartment_name: compartment.compartment_name || compartment.compartment_id || 'Compartimento não informado'
            }))
        );
    }
}
