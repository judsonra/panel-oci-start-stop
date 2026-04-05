import { CommonModule } from '@angular/common';
import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { finalize } from 'rxjs';
import { ButtonModule } from 'primeng/button';
import { CardModule } from 'primeng/card';
import { DatePickerModule } from 'primeng/datepicker';
import { InputTextModule } from 'primeng/inputtext';
import { MeterGroupModule } from 'primeng/metergroup';
import { MessageModule } from 'primeng/message';
import { MultiSelectModule } from 'primeng/multiselect';
import { Table, TableModule } from 'primeng/table';
import { TabsModule } from 'primeng/tabs';
import { TagModule } from 'primeng/tag';
import { TooltipModule } from 'primeng/tooltip';
import { ApiService } from '@/app/core/api.service';
import { CostByCompartmentReportModel, ReportCompartmentCostModel, ReportDetailedCostModel } from '@/app/core/models';

type CompartmentSortField = 'compartment_name' | 'total_amount' | 'resource_count';
type SortDirection = 'asc' | 'desc';

interface MeterGroupItem {
    label: string;
    value: number;
    color: string;
    service_name: string;
    percentage_label: string;
    tooltip: string;
}

interface DailyCompositionRow {
    date: string;
    amount: number;
    composition: MeterGroupItem[];
}

interface DetailedCostTableRow extends ReportDetailedCostModel {
    date_label: string;
    compartment_label: string;
    service_label: string;
    sku_label: string;
    resource_label: string;
}

interface ToggleableColumnOption {
    field: 'compartment_label' | 'service_label' | 'sku_label' | 'resource_label';
    header: string;
}

@Component({
    selector: 'app-cost-by-compartment-page',
    standalone: true,
    imports: [CommonModule, FormsModule, ButtonModule, CardModule, DatePickerModule, InputTextModule, MeterGroupModule, MessageModule, MultiSelectModule, TableModule, TabsModule, TagModule, TooltipModule],
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
                        <p-datepicker
                            [ngModel]="selectedPeriodDate()"
                            [ngModelOptions]="{ standalone: true }"
                            view="month"
                            dateFormat="mm/yy"
                            [readonlyInput]="true"
                            appendTo="body"
                            (ngModelChange)="setSelectedPeriod($event)"
                        />
                    </label>
                </div>

                <div class="form-actions reports-actions">
                    <div class="reports-button-group">
                        <button
                            pButton
                            type="button"
                            icon="pi pi-search"
                            severity="success"
                            styleClass="reports-consult-button"
                            [disabled]="loading()"
                            pTooltip="Consultar"
                            tooltipPosition="top"
                            aria-label="Consultar"
                            (click)="loadReport()"
                        ></button>
                        <button
                            pButton
                            type="button"
                            icon="pi pi-refresh"
                            severity="secondary"
                            [disabled]="refreshing()"
                            pTooltip="Atualizar da OCI"
                            tooltipPosition="top"
                            aria-label="Atualizar da OCI"
                            (click)="refreshReport()"
                        ></button>
                        <a
                            pButton
                            [href]="csvUrl()"
                            target="_blank"
                            rel="noopener"
                            icon="pi pi-download"
                            severity="contrast"
                            pTooltip="Exportar CSV"
                            tooltipPosition="top"
                            aria-label="Exportar CSV"
                        ></a>
                    </div>
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
                        <strong>{{ detailedItems().length }}</strong>
                        <small>Lançamentos detalhados com data no período</small>
                    </div>
                </p-card>
            </section>

            <section class="instances-tabs-panel report-tabs-panel">
                <p-tabs [value]="activeTab()" (valueChange)="setActiveTab($event)">
                    <p-tablist>
                        <p-tab [value]="0">Totais por compartimento</p-tab>
                        <p-tab [value]="1">Custos diários do mês</p-tab>
                        <p-tab [value]="2">Composição do custo</p-tab>
                    </p-tablist>
                    <p-tabpanels>
                        <p-tabpanel [value]="0">
                            <div class="table-shell">
                                <p-table [value]="sortedCompartments()" responsiveLayout="scroll">
                                    <ng-template pTemplate="header">
                                        <tr>
                                            <th>
                                                <button
                                                    pButton
                                                    type="button"
                                                    text
                                                    severity="secondary"
                                                    styleClass="report-sort-button"
                                                    [label]="sortLabel('Compartimento', 'compartment_name')"
                                                    [icon]="sortIcon('compartment_name')"
                                                    (click)="toggleCompartmentSort('compartment_name')"
                                                ></button>
                                            </th>
                                            <th>
                                                <button
                                                    pButton
                                                    type="button"
                                                    text
                                                    severity="secondary"
                                                    styleClass="report-sort-button"
                                                    [label]="sortLabel('Total do mês', 'total_amount')"
                                                    [icon]="sortIcon('total_amount')"
                                                    (click)="toggleCompartmentSort('total_amount')"
                                                ></button>
                                            </th>
                                            <th>
                                                <button
                                                    pButton
                                                    type="button"
                                                    text
                                                    severity="secondary"
                                                    styleClass="report-sort-button"
                                                    [label]="sortLabel('Recursos/serviços', 'resource_count')"
                                                    [icon]="sortIcon('resource_count')"
                                                    (click)="toggleCompartmentSort('resource_count')"
                                                ></button>
                                            </th>
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
                            </div>
                        </p-tabpanel>

                        <p-tabpanel [value]="1">
                            <div class="table-shell">
                                <p-table [value]="dailyCompositionRows()" responsiveLayout="scroll">
                                    <ng-template pTemplate="header">
                                        <tr>
                                            <th>Data</th>
                                            <th>Total</th>
                                            <th>Composição</th>
                                        </tr>
                                    </ng-template>
                                    <ng-template pTemplate="body" let-day>
                                        <tr>
                                            <td>{{ day.date | date: 'dd/MM/yyyy':'UTC' }}</td>
                                            <td>{{ formatMoney(day.amount) }}</td>
                                            <td class="report-meter-cell">
                                                @if (day.composition.length) {
                                                    <p-metergroup [value]="day.composition">
                                                        <ng-template #meter let-item let-class="class" let-size="size">
                                                            <span
                                                                [class]="class"
                                                                [style.background]="item.color"
                                                                [style.width]="size"
                                                                class="report-meter-segment"
                                                                [pTooltip]="item.tooltip"
                                                                tooltipPosition="top"
                                                            ></span>
                                                        </ng-template>
                                                        <ng-template #label let-item>
                                                            <span class="report-meter-label">{{ item.label }}</span>
                                                        </ng-template>
                                                    </p-metergroup>
                                                } @else {
                                                    <span class="report-empty-cell">Sem composição detalhada</span>
                                                }
                                            </td>
                                        </tr>
                                    </ng-template>
                                </p-table>
                            </div>
                        </p-tabpanel>

                        <p-tabpanel [value]="2">
                            <div class="table-shell">
                                <p-table
                                    #advancedTable
                                    [value]="detailedItems()"
                                    responsiveLayout="scroll"
                                    [paginator]="true"
                                    [rows]="15"
                                    [rowsPerPageOptions]="[15, 30, 60]"
                                    [globalFilterFields]="detailedGlobalFilterFields"
                                    sortField="date_label"
                                    [sortOrder]="-1"
                                    [showCurrentPageReport]="true"
                                    currentPageReportTemplate="Mostrando {first} a {last} de {totalRecords} itens"
                                    dataKey="date_label"
                                    styleClass="report-advanced-table"
                                >
                                    <ng-template pTemplate="caption">
                                        <div class="report-table-toolbar">
                                            <div class="report-table-toolbar-copy">
                                                <strong>Composição detalhada</strong>
                                                <small>Filtre os itens retornados pelo microserviço reports e escolha as colunas visíveis.</small>
                                            </div>

                                            <div class="report-table-toolbar-actions">
                                                <label class="report-toolbar-field report-column-toggle">
                                                    <span>Colunas</span>
                                                    <p-multiselect
                                                        [options]="toggleableColumns"
                                                        optionLabel="header"
                                                        optionValue="field"
                                                        [ngModel]="visibleColumnFields()"
                                                        [ngModelOptions]="{ standalone: true }"
                                                        display="chip"
                                                        defaultLabel="Selecionar colunas"
                                                        selectedItemsLabel="{0} colunas"
                                                        appendTo="body"
                                                        placeholder="Selecionar colunas"
                                                        (ngModelChange)="setVisibleColumnFields($event)"
                                                    />
                                                </label>

                                                <label class="report-toolbar-field report-search-field">
                                                    <span>Busca global</span>
                                                    <input
                                                        pInputText
                                                        type="text"
                                                        [value]="detailedSearchTerm()"
                                                        placeholder="Buscar em Data, Compartimento, Serviço, SKU ou Recurso"
                                                        (input)="applyDetailedGlobalFilter(advancedTable, $event)"
                                                    />
                                                </label>
                                                <button
                                                    pButton
                                                    type="button"
                                                    label="Limpar filtros"
                                                    icon="pi pi-filter-slash"
                                                    severity="secondary"
                                                    [outlined]="true"
                                                    (click)="clearDetailedTable(advancedTable)"
                                                ></button>
                                            </div>
                                        </div>
                                    </ng-template>
                                    <ng-template pTemplate="header">
                                        <tr>
                                            <th>
                                                <div class="report-header-cell">
                                                    <span>Data</span>
                                                    <p-columnFilter type="text" field="date_label" display="menu" [showMatchModes]="false" [showOperator]="false" [showAddButton]="false"></p-columnFilter>
                                                </div>
                                            </th>
                                            @if (isColumnVisible('compartment_label')) {
                                                <th>
                                                    <div class="report-header-cell">
                                                        <span>Compartimento</span>
                                                        <p-columnFilter type="text" field="compartment_label" display="menu" [showMatchModes]="false" [showOperator]="false" [showAddButton]="false"></p-columnFilter>
                                                    </div>
                                                </th>
                                            }
                                            @if (isColumnVisible('service_label')) {
                                                <th>
                                                    <div class="report-header-cell">
                                                        <span>Serviço</span>
                                                        <p-columnFilter type="text" field="service_label" display="menu" [showMatchModes]="false" [showOperator]="false" [showAddButton]="false"></p-columnFilter>
                                                    </div>
                                                </th>
                                            }
                                            @if (isColumnVisible('sku_label')) {
                                                <th>
                                                    <div class="report-header-cell">
                                                        <span>SKU</span>
                                                        <p-columnFilter type="text" field="sku_label" display="menu" [showMatchModes]="false" [showOperator]="false" [showAddButton]="false"></p-columnFilter>
                                                    </div>
                                                </th>
                                            }
                                            @if (isColumnVisible('resource_label')) {
                                                <th>
                                                    <div class="report-header-cell">
                                                        <span>Recurso</span>
                                                        <p-columnFilter type="text" field="resource_label" display="menu" [showMatchModes]="false" [showOperator]="false" [showAddButton]="false"></p-columnFilter>
                                                    </div>
                                                </th>
                                            }
                                            <th class="report-amount-column">
                                                <div class="report-header-cell report-header-cell-end">
                                                    <span>Total</span>
                                                    <p-columnFilter
                                                        type="numeric"
                                                        field="total_amount"
                                                        display="menu"
                                                        [showMatchModes]="false"
                                                        [showOperator]="false"
                                                        [showAddButton]="false"
                                                    ></p-columnFilter>
                                                </div>
                                            </th>
                                        </tr>
                                    </ng-template>
                                    <ng-template pTemplate="body" let-item>
                                        <tr>
                                            <td>{{ item.date_label }}</td>
                                            @if (isColumnVisible('compartment_label')) {
                                                <td>{{ item.compartment_label }}</td>
                                            }
                                            @if (isColumnVisible('service_label')) {
                                                <td>{{ item.service_label }}</td>
                                            }
                                            @if (isColumnVisible('sku_label')) {
                                                <td>{{ item.sku_label }}</td>
                                            }
                                            @if (isColumnVisible('resource_label')) {
                                                <td>
                                                    <span [pTooltip]="item.resource_label" tooltipPosition="top">
                                                        {{ formatResourceLabel(item.resource_label) }}
                                                    </span>
                                                </td>
                                            }
                                            <td class="report-amount-column">{{ formatMoney(item.total_amount) }}</td>
                                        </tr>
                                    </ng-template>
                                    <ng-template pTemplate="emptymessage">
                                        <tr>
                                            <td [attr.colspan]="visibleDetailedColumnCount()">
                                                <div class="report-empty-state">
                                                    <strong>Nenhum item encontrado.</strong>
                                                    <span>Ajuste os filtros ou consulte outro período para ver a composição do custo.</span>
                                                </div>
                                            </td>
                                        </tr>
                                    </ng-template>
                                </p-table>
                            </div>
                        </p-tabpanel>
                    </p-tabpanels>
                </p-tabs>
            </section>
        }
    `
})
export class CostByCompartmentPage implements OnInit {
    private readonly api = inject(ApiService);
    private readonly now = new Date();
    private readonly meterColors = ['#bb5a2f', '#d98841', '#6c9a8b', '#3d6f73', '#c3a35b', '#8c6a43'];

    readonly report = signal<CostByCompartmentReportModel | null>(null);
    readonly loading = signal(false);
    readonly refreshing = signal(false);
    readonly feedback = signal<string | null>(null);
    readonly feedbackSeverity = signal<'success' | 'error'>('success');
    readonly selectedPeriodDate = signal(new Date(this.now.getFullYear(), this.now.getMonth(), 1));
    readonly activeTab = signal(0);
    readonly compartmentSortField = signal<CompartmentSortField>('total_amount');
    readonly compartmentSortDirection = signal<SortDirection>('desc');
    readonly detailedSearchTerm = signal('');
    readonly detailedGlobalFilterFields = ['date_label', 'compartment_label', 'service_label', 'sku_label', 'resource_label'];
    readonly toggleableColumns: ToggleableColumnOption[] = [
        { field: 'compartment_label', header: 'Compartimento' },
        { field: 'service_label', header: 'Serviço' },
        { field: 'sku_label', header: 'SKU' },
        { field: 'resource_label', header: 'Recurso' }
    ];
    readonly visibleColumnFields = signal<ToggleableColumnOption['field'][]>(this.toggleableColumns.map((column) => column.field));
    readonly selectedMonth = computed(() => this.selectedPeriodDate().getMonth() + 1);
    readonly selectedYear = computed(() => this.selectedPeriodDate().getFullYear());
    readonly csvUrl = computed(() => this.api.getCostByCompartmentCsvUrl(this.selectedYear(), this.selectedMonth()));
    readonly sortedCompartments = computed(() => this.sortCompartments(this.report()?.compartments || []));
    readonly detailedItems = computed(() => this.buildDetailedItems(this.report()?.detailed_items || []));
    readonly dailyCompositionRows = computed(() => this.buildDailyCompositionRows(this.report()));
    readonly visibleDetailedColumnCount = computed(() => 2 + this.visibleColumnFields().length);

    ngOnInit(): void {
        this.loadReport();
    }

    setActiveTab(value: string | number | undefined): void {
        const nextValue = typeof value === 'number' ? value : Number(value ?? 0);
        this.activeTab.set(Number.isNaN(nextValue) ? 0 : nextValue);
    }

    setSelectedPeriod(value: Date | Date[] | null | undefined): void {
        const nextDate = value instanceof Date ? value : Array.isArray(value) ? value[0] : null;
        if (!(nextDate instanceof Date) || Number.isNaN(nextDate.getTime())) {
            return;
        }
        this.selectedPeriodDate.set(new Date(nextDate.getFullYear(), nextDate.getMonth(), 1));
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

    toggleCompartmentSort(field: CompartmentSortField): void {
        if (this.compartmentSortField() === field) {
            this.compartmentSortDirection.set(this.compartmentSortDirection() === 'asc' ? 'desc' : 'asc');
            return;
        }
        this.compartmentSortField.set(field);
        this.compartmentSortDirection.set(field === 'total_amount' ? 'desc' : 'asc');
    }

    sortLabel(label: string, field: CompartmentSortField): string {
        if (this.compartmentSortField() !== field) {
            return label;
        }
        return `${label} ${this.compartmentSortDirection() === 'asc' ? '↑' : '↓'}`;
    }

    sortIcon(field: CompartmentSortField): string {
        if (this.compartmentSortField() !== field) {
            return 'pi pi-sort-alt';
        }
        return this.compartmentSortDirection() === 'asc' ? 'pi pi-sort-amount-up' : 'pi pi-sort-amount-down';
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

    applyDetailedGlobalFilter(table: Table, event: Event): void {
        const value = String((event.target as HTMLInputElement | null)?.value ?? '');
        this.detailedSearchTerm.set(value);
        table.filterGlobal(value, 'contains');
    }

    clearDetailedTable(table: Table): void {
        this.detailedSearchTerm.set('');
        table.clear();
    }

    setVisibleColumnFields(value: ToggleableColumnOption['field'][] | null | undefined): void {
        const nextValue = Array.isArray(value) ? value.filter((field): field is ToggleableColumnOption['field'] => this.toggleableColumns.some((column) => column.field === field)) : [];
        this.visibleColumnFields.set(nextValue);
    }

    isColumnVisible(field: ToggleableColumnOption['field']): boolean {
        return this.visibleColumnFields().includes(field);
    }

    formatResourceLabel(value: string): string {
        if (!value || value === '-' || value.length <= 28) {
            return value || '-';
        }
        return `${value.slice(0, 20)}...${value.slice(-5)}`;
    }

    private sortCompartments(compartments: ReportCompartmentCostModel[]): ReportCompartmentCostModel[] {
        const field = this.compartmentSortField();
        const direction = this.compartmentSortDirection() === 'asc' ? 1 : -1;
        return [...compartments].sort((left, right) => {
            if (field === 'total_amount') {
                return (left.total_amount - right.total_amount) * direction;
            }
            if (field === 'resource_count') {
                return (left.resources.length - right.resources.length) * direction;
            }

            const leftValue = (left.compartment_name || left.compartment_id || 'Compartimento não informado').toLocaleLowerCase('pt-BR');
            const rightValue = (right.compartment_name || right.compartment_id || 'Compartimento não informado').toLocaleLowerCase('pt-BR');
            return leftValue.localeCompare(rightValue, 'pt-BR') * direction;
        });
    }

    private buildDetailedItems(items: ReportDetailedCostModel[]): DetailedCostTableRow[] {
        return items.map((item) => ({
            ...item,
            date_label: this.formatDate(item.date),
            compartment_label: item.compartment_name || item.compartment_id || 'Compartimento não informado',
            service_label: item.service || '-',
            sku_label: item.sku_name || '-',
            resource_label: item.resource_name || item.resource_id || '-'
        }));
    }

    private buildDailyCompositionRows(report: CostByCompartmentReportModel | null): DailyCompositionRow[] {
        if (!report) {
            return [];
        }

        const items = report.detailed_items || [];
        if (!items.length) {
            return (report.daily_totals || []).map((day) => ({
                ...day,
                composition: this.buildFallbackDayComposition(report.compartments || [], day.date)
            }));
        }

        const byDay = new Map<string, Map<string, number>>();
        for (const item of items) {
            const dayMap = byDay.get(item.date) ?? new Map<string, number>();
            const key = item.service || item.compartment_name || item.compartment_id || 'Outros';
            dayMap.set(key, (dayMap.get(key) || 0) + item.total_amount);
            byDay.set(item.date, dayMap);
        }

        return (report.daily_totals || []).map((day) => ({
            ...day,
            composition: this.buildMeterItems(byDay.get(day.date))
        }));
    }

    private buildFallbackDayComposition(compartments: ReportCompartmentCostModel[], date: string): MeterGroupItem[] {
        const dayMap = new Map<string, number>();
        for (const compartment of compartments) {
            const day = compartment.daily_costs.find((item) => item.date === date);
            if (!day || day.amount <= 0) {
                continue;
            }
            dayMap.set(compartment.compartment_name || compartment.compartment_id || 'Outros', day.amount);
        }
        return this.buildMeterItems(dayMap);
    }

    private buildMeterItems(source: Map<string, number> | undefined): MeterGroupItem[] {
        if (!source || source.size === 0) {
            return [];
        }

        const total = [...source.values()].reduce((sum, value) => sum + value, 0);

        return [...source.entries()]
            .sort((left, right) => right[1] - left[1])
            .map(([label, value], index) => ({
                label: `${label} ${this.formatPercentage(total > 0 ? value / total : 0)}`,
                value,
                color: this.meterColors[index % this.meterColors.length],
                service_name: label,
                percentage_label: this.formatPercentage(total > 0 ? value / total : 0),
                tooltip: `Serviço: ${label} | Percentual: ${this.formatPercentage(total > 0 ? value / total : 0)}`
            }));
    }

    private formatDate(value: string): string {
        return new Intl.DateTimeFormat('pt-BR', {
            timeZone: 'UTC',
            day: '2-digit',
            month: '2-digit',
            year: 'numeric'
        }).format(new Date(`${value}T00:00:00Z`));
    }

    private formatPercentage(value: number): string {
        return new Intl.NumberFormat('pt-BR', {
            style: 'percent',
            minimumFractionDigits: 1,
            maximumFractionDigits: 1
        }).format(value);
    }
}
